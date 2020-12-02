#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# (c) Grupo AIA
#     gaitanv@aia.es
#     marinjl@aia.es
#
#
# calc_curve_diffmetrics.py:
#
# Given a directory containing processed Astre and Dynawo cases, all
# of them derived from a common base case, this script calculates
# several metrics that try to assess the differences in various curve
# data (such as voltages, power, and K-level values vs. time).  It
# works on the curve files produced by Astre and Dynawo, where
# variable names have been suitably prepared in order to have the same
# names.
#
#   * On input: you have to provide the directory that contains the
#     files that have the output curves (e.g. "*-AstreCurves.csv.xz",
#     etc.), plus a filename prefix for them (e.g. "shunt_").
#
#   * On output: TODO
#
#

import sys
import os
import glob
from pathlib import Path
from collections import namedtuple
import pandas as pd
import numpy as np

AST_SUFFIX = "-AstreCurves.csv.xz"
DWO_SUFFIX = "-DynawoCurves.csv.xz"
TFIN_TIME_OFFSET = 4000  # Dynawo's tFin time offset w.r.t. Astre
EPS = 1.0e-6

verbose = True


def main():

    if len(sys.argv) != 3:
        print("\nUsage: %s CRV_DIR PREFIX\n" % sys.argv[0])
        return 2
    crv_dir = sys.argv[1]
    prefix = sys.argv[2]

    # Check all needed dirs are in place, and get the list of files to process
    file_list = check_inputfiles(crv_dir, prefix, verbose)
    print("Calculating diffmetrics for curve data in: %s" % crv_dir)

    # Calculate all diffmetrics and output the results to file
    process_all_curves(crv_dir, file_list)

    return 0


def check_inputfiles(crv_dir, prefix, verbose=False):
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


def process_all_curves(crv_dir, file_list):

    cnames = ["v_ini", "v_fin", "t_trans", "max_trans", "min_trans", "peri", "damp"]

    all_ast = pd.DataFrame()
    all_dwo = pd.DataFrame()

    print("Processing ", end="")
    for case_label in file_list:
        print(".", end="", flush=True)
        ast_file = file_list[case_label].ast
        dwo_file = file_list[case_label].dwo

        df_ast = pd.read_csv(ast_file, sep=";", compression="infer")
        df_dwo = pd.read_csv(dwo_file, sep=";", compression="infer")
        df_dwo = df_dwo.iloc[:, :-1]  # because of extra ";" at end-of-lines
        df_dwo["time"] = df_dwo.time - TFIN_TIME_OFFSET

        # Check vars. They match by order, not necessarily by name
        if len(df_ast.columns) != len(df_dwo.columns):
            raise ValueError(
                "Dinawo and Astre curve data differ in the number of fields (case %s)\n"
                % case_label
            )
        df_ast.columns = df_dwo.columns
        vars_ast = df_ast.columns[1:]
        vars_dwo = df_dwo.columns[1:]

        res_ast = [analyze_crv(df_ast, x) for x in vars_ast]
        res_dwo = [analyze_crv(df_dwo, x) for x in vars_dwo]

        dd_ast = pd.DataFrame(data=res_ast, columns=cnames)
        dd_dwo = pd.DataFrame(data=res_dwo, columns=cnames)
        dd_ast["vars"] = vars_ast
        dd_dwo["vars"] = vars_dwo
        dd_ast["dev"] = case_label
        dd_dwo["dev"] = case_label
        all_ast = all_ast.append(dd_ast)
        all_dwo = all_dwo.append(dd_dwo)

    print(" OK.")

    # Calculate diffs in metrics
    delta = all_ast[["dev", "vars"]].copy(deep=True)
    delta["dSS_ast"] = all_ast.v_fin - all_ast.v_ini
    delta["dSS_dwo"] = all_dwo.v_fin - all_dwo.v_ini
    delta["dPP_ast"] = all_ast.max_trans - all_ast.min_trans
    delta["dPP_dwo"] = all_dwo.max_trans - all_dwo.min_trans
    delta["TT_ast"] = all_ast.t_trans
    delta["TT_dwo"] = all_dwo.t_trans
    delta["period_ast"] = all_ast.peri
    delta["period_dwo"] = all_dwo.peri
    delta["damp_ast"] = all_ast.damp
    delta["damp_dwo"] = all_dwo.damp

    # Output to file
    metrics_dir = crv_dir + "/../metrics"
    Path(metrics_dir).mkdir(parents=False, exist_ok=True)
    all_ast.to_csv(metrics_dir + "/curve_metrics_ast.csv", sep=";", index=False)
    all_dwo.to_csv(metrics_dir + "/curve_metrics_dwo.csv", sep=";", index=False)
    delta.to_csv(metrics_dir + "/curve_diffmetrics.csv", sep=";", index=False)
    print("Saved diffmetrics for curve data in: %s" % metrics_dir)


##############################################################################
# Data analisys
# returns 'vini', 'v_fin', 't_trans', 'max_trans', 'min_trans','freq','damp'
##############################################################################
def analyze_crv(df, vv):
    x = df[vv].values
    t = df["time"].values

    dd = np.where(np.abs(np.diff(x)) > EPS)[0]
    dd = dd[np.where(dd > 3)]

    if len(dd) == 0:
        return [x[0], x[0], 0, 0, 0, 0, 0]

    ll = len(dd)
    xin = x[dd[0]]
    x0 = x[dd[0] + 1]
    ifin = dd[ll - 1] + 1
    if ifin < 300:
        ifin = 300
    xfin = x[ifin]
    ttran = t[ifin] - 300
    xmax = max(x[dd]) - x0
    xmin = min(x[dd]) - x0

    if len(x) > 200:
        x = subsample(x, 16)
        dd = dd // 16
    fsamp = len(x) / 1200

    x = x[dd[0] + 5 :]
    x = x - np.mean(x)
    peri, damp = get_peri_damp(x, fsamp)
    return [xin, xfin, ttran, xmax, xmin, peri, damp]


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
        return ([1, 0], [1, 0], 0)

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

    return (b, a, err)


def subsample(x, d):
    t = np.arange(len(x))
    return x[t % d == 0]


def get_freq_damp(x, fsamp):
    p = 5
    q = 4
    b, a, err = prony(x, p, q)
    lamb = fsamp * np.log(np.roots(a))[0]

    freq = np.abs(np.imag(lamb)) / (2 * np.pi)
    damp = np.abs(np.real(lamb) / np.abs(lamb))

    mask = np.argmin(freq)

    freq = freq[mask]
    damp = damp[mask]
    return (freq, damp)


def get_peri_damp(x, fsamp):
    p = 7
    q = 6
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
    return (peri, damp)


if __name__ == "__main__":
    sys.exit(main())
