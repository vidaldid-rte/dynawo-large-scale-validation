#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     gaitanv@aia.es
#     marinjl@aia.es
#
# calc_curve_diffmetrics.py: Given a directory containing processed Astre and Dynawo
# cases, all of them derived from a common base case, this script extracts several
# "reduced parameters" that characterize the curve signals. It works on the curve
# files produced by Astre and Dynawo, where variable names have been suitably
# prepared in order to have the same names.
#
#   * On input: you have to provide the directory that contains the curve files (e.g.
#     "*-AstreCurves.csv.xz", etc.), a filename prefix for them (e.g. "shunt_"), and the
#     time at which the contingency takes place (e.g. 300).
#
#   * On output: a file "crv_reducedparams.csv" containing dSS, dPP, etc. for all cases
#     and all variables, for Dynawo and Astre values.
#

import sys
import os
import glob
from pathlib import Path
from collections import namedtuple
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d
from calc_diffmetrics_common import get_time_params


REL_TOL = 1.0e-5  # when testing for the SS, relative tolerance in signal
STABILITY_MINTIME = 60  # require at least these seconds for the SS to be achieved
TT_MIN_FOR_PRONY = 60  # transient must be at least these seconds long to do Prony
PRONY_ORDER = 7  # number of damped sinusoid components
PRONY_SAMPLES = 100  # number of (interpolated) data points used for Prony analysis
AST_SUFFIX = "-AstreCurves.csv.xz"
DWO_SUFFIX = "-DynawoCurves.csv.xz"
verbose = True


def main():
    if len(sys.argv) != 4:
        print("\nUsage: %s CRV_DIR PREFIX BASECASE\n" % sys.argv[0])
        return 2
    crv_dir = sys.argv[1]
    prefix = sys.argv[2]
    base_case = sys.argv[3]

    # Check all needed dirs are in place, and get the list of files to process
    file_list = check_inputfiles(crv_dir, prefix)
    print("Calculating diffmetrics for curve data in: %s" % crv_dir)

    # Obtain the time at which the contingency takes place
    startTime, _, t_event = get_time_params(base_case, verbose)

    # Calculate all diffmetrics and output the results to file
    process_all_curves(crv_dir, file_list, startTime, t_event)

    return 0


def check_inputfiles(crv_dir, prefix):
    if not os.path.isdir(crv_dir):
        raise ValueError("input directory %s not found" % crv_dir)

    # We first find out all Astre files
    ast_filepattern = crv_dir + "/" + prefix + "*" + AST_SUFFIX
    ast_files = glob.glob(ast_filepattern)
    if len(ast_files) == 0:
        raise ValueError("no input files found with prefix %s\n" % prefix)

    # Then we find their corresponding Dynawo counterparts
    Crv_Pair = namedtuple("Crv_Pair", ["ast", "dwo"])
    file_list = dict()
    for ast_file in ast_files:
        case_label = ast_file.split(AST_SUFFIX)[0].split(prefix)[-1]
        dwo_file = ast_file.split(AST_SUFFIX)[0] + DWO_SUFFIX
        if not (os.path.isfile(dwo_file)):
            raise ValueError("Dinawo data file not found for %s\n" % ast_file)
        file_list[case_label] = Crv_Pair(ast=ast_file, dwo=dwo_file)

    if verbose:
        print("crv_dir: %s" % crv_dir)
        print("prefix: %s" % prefix)
        print("List of cases to process: (total: %d)" % len(file_list))
        case_list = sorted(file_list.keys())
        if len(case_list) < 10:
            print(case_list)
        else:
            print(case_list[:5] + ["..."] + case_list[-5:])
        print()

    return file_list


def process_all_curves(crv_dir, file_list, startTime, t_event):

    all_ast = pd.DataFrame()
    all_dwo = pd.DataFrame()
    cnames = ["dSS", "dPP", "TT", "period", "damping", "is_preStab", "is_postStab"]
    t0_event = t_event - startTime

    print("Processing ", end="")
    for case_label in file_list:
        crv_ast = pd.read_csv(file_list[case_label].ast, sep=";", compression="infer")
        crv_dwo = pd.read_csv(file_list[case_label].dwo, sep=";", compression="infer")
        crv_dwo = crv_dwo.iloc[:, :-1]  # because of extra ";" at end-of-lines
        # Check vars. They should match by order AND name
        if list(crv_ast.columns) != list(crv_dwo.columns):
            raise ValueError(
                "Dynawo and Astre curves differ in name or number of fields (case %s)\n"
                % case_label
            )
        # Check that Dynawo's simulation startTime is consistent, and
        # adjust the time offset w.r.t. Astre
        dwo_crv_startTime = crv_dwo["time"].iloc[0]
        if dwo_crv_startTime != startTime:
            raise ValueError(
                "The startTime in Dynawo curve file (case %s) differs from BASECASE!\n"
                % case_label
            )
        crv_dwo["time"] = crv_dwo["time"] - startTime
        # Check for simulations that stopped before the end
        if crv_ast["time"].iloc[-1] != crv_dwo["time"].iloc[-1]:
            print(
                "   WARNING: Dynawo and Astre curves stop at differet times (case %s)\n"
                % case_label
            )

        # Process all variables for this case
        var_list = list(crv_dwo.columns)[1:]
        res_ast = [extract_crv_reduced_params(crv_ast, x, t0_event) for x in var_list]
        res_dwo = [extract_crv_reduced_params(crv_dwo, x, t0_event) for x in var_list]

        # Structure the results in a dataframe
        case_ast = pd.DataFrame(data=res_ast, columns=cnames)
        case_dwo = pd.DataFrame(data=res_dwo, columns=cnames)
        case_ast["dev"] = case_label
        case_dwo["dev"] = case_label
        case_ast["vars"] = var_list
        case_dwo["vars"] = var_list

        # Collect results for all cases
        all_ast = all_ast.append(case_ast)
        all_dwo = all_dwo.append(case_dwo)
        print(".", end="", flush=True)

    print(" OK.")

    # Group all reduced signal parameters in one single dataframe
    reduced_params = all_ast[["dev", "vars"]].copy(deep=True)
    reduced_params["dSS_ast"] = all_ast.dSS
    reduced_params["dSS_dwo"] = all_dwo.dSS
    reduced_params["dPP_ast"] = all_ast.dPP
    reduced_params["dPP_dwo"] = all_dwo.dPP
    reduced_params["TT_ast"] = all_ast.TT
    reduced_params["TT_dwo"] = all_dwo.TT
    reduced_params["period_ast"] = all_ast.period
    reduced_params["period_dwo"] = all_dwo.period
    reduced_params["damp_ast"] = all_ast.damping
    reduced_params["damp_dwo"] = all_dwo.damping
    reduced_params["is_preStab_ast"] = all_ast.is_preStab
    reduced_params["is_preStab_dwo"] = all_dwo.is_preStab
    reduced_params["is_postStab_ast"] = all_ast.is_postStab
    reduced_params["is_postStab_dwo"] = all_dwo.is_postStab

    # Output to file
    metrics_dir = crv_dir + "/../metrics"
    Path(metrics_dir).mkdir(parents=False, exist_ok=True)
    reduced_params.to_csv(
        metrics_dir + "/crv_reducedparams.csv",
        sep=";",
        index=False,
        float_format="%.6f",
    )
    print("Saved reduced parameters for curve data under: %s" % metrics_dir)


#################################################################################
# Extraction of the relevant reduced parameters for the curve (dSS, dPP, etc.)
#################################################################################
def extract_crv_reduced_params(df, var, t_event):
    # Summary:
    #   * Initial Steady State value: taken from the instant right before the event
    #   * Final Steady State value: taken from the very last instant
    #   * With these, we calculate dSS and dPP
    #   * Transient end: defined as the time at which all subsequent values are within
    #     some (relative) tolerance of the final Steady State value.
    #   * Tag whether the case is pre-contingency & post-contingency stable
    #   * Window the transient and do Prony analysis to calculate period & damping of
    #     the main component
    #
    # Stability (pre or post) is defined as "signal has not deviated from the last
    # value more than REL_TOL (relative error), for at least STABILITY_MINTIME seconds"
    #

    x = df[var].values
    t = df["time"].values

    # Net change in steady state (dSS):
    idx_SSpre = np.nonzero(t < t_event)[0][-1]
    idx_SSpost = -1
    dSS = x[idx_SSpost] - x[idx_SSpre]

    # Peak-to-peak amplitude (sPP):
    dPP = np.max(x[t >= t_event]) - np.min(x[t >= t_event])

    # Transient time (TT):
    tol = max(abs(x[idx_SSpost]) * REL_TOL, REL_TOL)
    idx_transientEnd = np.nonzero((t >= t_event) & (np.abs(x - x[idx_SSpost]) < tol))[
        0
    ][0]
    TT = t[idx_transientEnd] - t_event

    # Post-contingency stability:
    if (t[-1] - t[idx_transientEnd]) >= STABILITY_MINTIME:
        is_postStab = True
    else:
        is_postStab = False

    # Pre-contingency stability:
    tol = max(abs(x[idx_SSpre]) * REL_TOL, REL_TOL)
    idx_preTransientEnd = np.nonzero((t < t_event) & (np.abs(x - x[idx_SSpre]) < tol))[
        0
    ][0]
    if (t_event - t[idx_preTransientEnd]) >= STABILITY_MINTIME:
        is_preStab = True
    else:
        is_preStab = False

    # Period and damping of the transient (via Prony analysis):
    # first, trim the signal to the transient window
    idx_transientStart = np.nonzero(t > t_event)[0][0]
    if (
        TT < TT_MIN_FOR_PRONY
        or (idx_transientEnd - idx_transientStart) < 2 * PRONY_ORDER
    ):
        # transient too short for any meaningful Prony analysis
        return [dSS, dPP, TT, 0, 0, is_preStab, is_postStab]
    t_trans = t[idx_transientStart:idx_transientEnd]
    x_trans = x[idx_transientStart:idx_transientEnd]
    # then, smooth out the kinks
    t_trans, x_trans = avg_duplicate_points(t_trans, x_trans)
    # now, interpolate to get samples that are equally-spaced in time (because Dynawo's
    # time-step could be variable)
    f = interp1d(t_trans, x_trans, kind="cubic")
    t_interp = np.linspace(t_trans[0], t_trans[-1], num=PRONY_SAMPLES, endpoint=True)
    x_interp = f(t_interp)
    # and finally, do the Prony analysis
    sampling_rate = len(x_interp) / (t_interp[-1] - t_interp[0])
    x_interp = x_interp - np.mean(x_interp)
    period, damping = get_peri_damp(x_interp, sampling_rate)

    return [dSS, dPP, TT, period, damping, is_preStab, is_postStab]


# Both Astre and Dynawo may output two data points with the same timestamp. This
# function cleans the signal by taking the average of such cases.  Uses the elegant
# solution given by Gabriel S. Gusmão (see https://stackoverflow.com/questions/7790611)
def avg_duplicate_points(t_orig, x_orig):
    t, ind, counts = np.unique(t_orig, return_index=True, return_counts=True)
    x = x_orig[ind]
    for dup in t[counts > 1]:
        x[t == dup] = np.average(x_orig[t_orig == dup])
    return t, x


#################################
# Prony analysis
#################################
def convm(x, p):
    """Generates a convolution matrix

    Usage: X = convm(x,p)
    Given a vector x of length N, an N+p-1 by p convolution matrix is
    generated of the following form:
              |  x(0)  0      0     ...      0    |
              |  x(1) x(0)    0     ...      0    |
              |  x(2) x(1)   x(0)   ...      0    |
         X =  |   .    .      .              .    |
              |   .    .      .              .    |
              |   .    .      .              .    |
              |  x(N) x(N-1) x(N-2) ...  x(N-p+1) |
              |   0   x(N)   x(N-1) ...  x(N-p+2) |
              |   .    .      .              .    |
              |   .    .      .              .    |
              |   0    0      0     ...    x(N)   |

    That is, x is assumed to be causal, and zero-valued after N.
    """
    N = len(x) + 2 * p - 2
    xpad = np.concatenate([np.zeros(p - 1), x[:], np.zeros(p - 1)])
    X = np.zeros((len(x) + p - 1, p))
    # Construct X column by column
    for i in range(p):
        X[:, i] = xpad[p - i - 1 : N - i]

    return X


def prony(x, p, q):
    """Model a signal using Prony's method

    Usage: [b,a,err] = prony(x,p,q)

    The input sequence x is modeled as the unit sample response of
    a filter having a system function of the form
        H(z) = B(z)/A(z)
    The polynomials B(z) and A(z) are formed from the vectors
        b=[b(0), b(1), ... b(q)]
        a=[1   , a(1), ... a(p)]
    The input q defines the number of zeros in the model
    and p defines the number of poles. The modeling error is
    returned in err.

    This comes from Hayes, p. 149, 153, etc

    """
    x = x[:]
    N = len(x)
    if p + q >= len(x):
        return [1, 0], [1, 0], 0

    # This formulation uses eq. 4.50, p. 153
    # Set up the convolution matrices
    X = convm(x, p + 1)
    Xq = X[q : N + p - 1, 0:p]
    xq1 = -X[q + 1 : N + p, 0]

    # Solve for denominator coefficients
    if p > 0:
        a = np.linalg.lstsq(Xq, xq1, rcond=None)[0]
        a = np.insert(a, 0, 1)  # a(0) is 1
    else:
        # all-zero model
        a = np.array(1)

    # Solve for the model error
    err = np.dot(x[q + 1 : N].conj().T, X[q + 1 : N, 0 : p + 1])
    err = np.dot(err, a)

    # Solve for numerator coefficients
    if q > 0:
        # (This is the same as for Pad?)
        b = np.dot(X[0 : q + 1, 0 : p + 1], a)
    else:
        # all-pole model
        # b(0) is x(0), but a better solution is to match energy
        b = np.sqrt(err)

    return b, a, err


def get_peri_damp(x, fsamp):
    p = PRONY_ORDER
    q = PRONY_ORDER - 1
    b, a, err = prony(x, p, q)
    with np.errstate(divide="ignore"):  # we may get some Inf here
        lamb = fsamp * np.log(np.roots(a))

    freq = np.abs(np.imag(lamb)) / (2 * np.pi)

    with np.errstate(invalid="ignore"):  # we may get some NaN here (0/0)
        damp = np.real(lamb) / np.abs(lamb)

    mask = np.argmin(freq)
    freq = freq[mask]
    damp = damp[mask]

    if freq == 0:
        peri = 0
    else:
        peri = 1 / freq

    return peri, damp


if __name__ == "__main__":
    sys.exit(main())
