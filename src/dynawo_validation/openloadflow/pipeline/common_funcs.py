# Common functions for all contingency-generating scripts
import os
import sys
import glob
import subprocess
import pandas as pd
from lxml import etree
from collections import namedtuple

# TODO: Remove unused code
# def check_inputfiles(input_case, dwo_paths, verbose=False):
#     if not os.path.isdir(input_case):
#         raise ValueError("source directory %s not found" % input_case)
#
#     # remove trailing slash so that basename/dirname below behave consistently:
#     if input_case[-1] == "/":
#         input_case = input_case[:-1]
#     basename = os.path.basename(input_case)
#     dirname = os.path.dirname(input_case)
#     # corner case: if called from the parent dir, dirname is empty
#     if dirname == "":
#         dirname = "."
#
#     print("\nUsing input_case: %s" % input_case)
#     print("New cases will be generated under: %s" % dirname)
#     if verbose:
#         print("input_case: %s" % input_case)
#         print("basename: %s" % basename)
#         print("dirname:  %s" % dirname)
#
#     if not (
#         os.path.isfile(input_case + "/Astre/donneesModelesEntree.xml")
#         and os.path.isfile(input_case + "/" + dwo_paths.iidmFile)
#         and os.path.isfile(input_case + "/" + dwo_paths.dydFile)
#         and os.path.isfile(input_case + "/" + dwo_paths.parFile)
#         and os.path.isfile(input_case + "/" + dwo_paths.curves_inputFile)
#     ):
#         raise ValueError("some expected files are missing in %s\n" % input_case)
#
#     return input_case, basename, dirname


# def copy_astdwo_basecase(base_case, dwo_paths, dest_case):
#     """Make the subdirs for the Astre and Dynawo cases; then copy all non-changed
#     files using symbolic links
#     """
#     # If the destination exists, first remove it
#     if os.path.exists(dest_case):
#         remove_case(dest_case)
#     # For Dynawo, obtain most paths from the info in the JOB file
#     iidm_dir = os.path.dirname(dwo_paths.iidmFile)
#     dyd_dir = os.path.dirname(dwo_paths.dydFile)  # all these are usually the same,
#     par_dir = os.path.dirname(dwo_paths.parFile)  # but we allow themm to be different,
#     crv_dir = os.path.dirname(dwo_paths.curves_inputFile)  # just in case
#     # Compose and execute the shell commands
#     full_command = f"mkdir -p '{dest_case}/Astre' '{dest_case}/{iidm_dir}'"
#     f" '{dest_case}/{dyd_dir}' '{dest_case}/{par_dir}' '{dest_case}/{crv_dir}'"
#     f" && ln -s '{dwo_paths.job_file}' '{dest_case}'"
#     f" && ln -s '{base_case}/{dwo_paths.iidmFile}' '{dest_case}/{iidm_dir}'"
#     try:
#         retcode = subprocess.call(full_command, shell=True)
#         if retcode < 0:
#             raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
#         elif retcode > 0:
#             raise ValueError("Copy operation returned error code: %d" % retcode)
#     except OSError as e:
#         print("Copy operation failed: ", e, file=sys.stderr)
#         raise


def copy_basecase(base_case, iidm_file, hades_file, param_file, dest_case):
    """Make the subdirs for the Hades and OLF cases; then copy all non-changed
    files using symbolic links

    """
    # If the destination exists, first remove it
    if os.path.exists(dest_case):
        remove_case(dest_case)

    # In the result dir layout, base file and contingencies are at the same level
    # Using relative path enables to copy the result dir as a standalone thing
    case_dir = "../" + os.path.basename(base_case)
    iidm_source =  os.path.join(case_dir, iidm_file)
    hades_source = os.path.join(case_dir, hades_file)
    param_source = os.path.join(case_dir, param_file)

    # Compose and execute the shell commands
    bc = base_case
    full_command = (
        f" mkdir -p '{dest_case}'"
        f" && ln -s '{iidm_source}' '{dest_case}'"
        f" && ln -s '{hades_source}' '{dest_case}'"
        f" && ln -s '{param_source}' '{dest_case}'"
    )
    try:
        retcode = subprocess.call(full_command, shell=True)
        if retcode < 0:
            raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("Copy operation returned error code: %d" % retcode)
    except OSError as e:
        print("Copy operation failed: ", e, file=sys.stderr)
        raise

#
# def copy_dwodwo_basecase(base_case, dwo_pathsA, dwo_pathsB, dest_case):
#     """Make the subdirs for the Hades and Dynawo cases; then copy all non-changed
#     files using symbolic links
#
#     """
#     # If the destination exists, first remove it
#     if os.path.exists(dest_case):
#         remove_case(dest_case)
#     # For Dynawo A, obtain most paths from the info in the JOB file
#     iidm_dirA = os.path.dirname(dwo_pathsA.iidmFile)
#     dyd_dirA = os.path.dirname(dwo_pathsA.dydFile)
#     spar_dirA = os.path.dirname(dwo_pathsA.solver_parFile)
#     npar_dirA = os.path.dirname(dwo_pathsA.network_parFile)
#     par_dirA = os.path.dirname(dwo_pathsA.parFile)
#     crv_dirA = os.path.dirname(dwo_pathsA.curves_inputFile)
#     contg_dyd_dirA = os.path.dirname(dwo_pathsA.dydFile_contg)
#     contg_par_dirA = os.path.dirname(dwo_pathsA.parFile_contg)
#     # For Dynawo B, obtain most paths from the info in the JOB file
#     iidm_dirB = os.path.dirname(dwo_pathsB.iidmFile)
#     dyd_dirB = os.path.dirname(dwo_pathsB.dydFile)
#     spar_dirB = os.path.dirname(dwo_pathsB.solver_parFile)
#     npar_dirB = os.path.dirname(dwo_pathsB.network_parFile)
#     par_dirB = os.path.dirname(dwo_pathsB.parFile)
#     crv_dirB = os.path.dirname(dwo_pathsB.curves_inputFile)
#     contg_dyd_dirB = os.path.dirname(dwo_pathsB.dydFile_contg)
#     contg_par_dirB = os.path.dirname(dwo_pathsB.parFile_contg)
#     # If base_case path is not absolute, symbolic links need this relative prefix
#     # This assumes that if it's not absolute, base_case & dest_case are at same level
#     if base_case[0] != "/":
#         p = "../"
#     else:
#         p = ""
#     # Special Diagrams dir is hard-coded (potential GOTCHA: we use the first match)
#     diagr_dirA = glob.glob(f"{base_case}/A/*_Diagram")
#     diagr_dirB = glob.glob(f"{base_case}/B/*_Diagram")
#     if len(diagr_dirA) != 0:
#         copy_diagr_commandA = f" && ln -s '{p}{p}{diagr_dirA[0]}' '{dest_case}/A'"
#     else:
#         copy_diagr_commandA = ""
#     if len(diagr_dirB) != 0:
#         copy_diagr_commandB = f" && ln -s '{p}{p}{diagr_dirB[0]}' '{dest_case}/B'"
#     else:
#         copy_diagr_commandB = ""
#     # Compose and execute the shell commands
#     bc = base_case
#     full_command = (
#         f"mkdir -p '{dest_case}/{par_dirA}' '{dest_case}/{par_dirB}'"
#         f" '{dest_case}/{crv_dirA}' '{dest_case}/{crv_dirB}'"
#         f" '{dest_case}/{spar_dirA}' '{dest_case}/{spar_dirB}'"
#         f" '{dest_case}/{npar_dirA}' '{dest_case}/{npar_dirB}'"
#         f" && ln -s '{p}{dwo_pathsA.job_file}' '{dest_case}'"
#         f" && ln -s '{p}{dwo_pathsB.job_file}' '{dest_case}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsA.iidmFile}' '{dest_case}/{iidm_dirA}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsB.iidmFile}' '{dest_case}/{iidm_dirB}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsA.dydFile}' '{dest_case}/{dyd_dirA}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsB.dydFile}' '{dest_case}/{dyd_dirB}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsA.parFile}' '{dest_case}/{par_dirA}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsB.parFile}' '{dest_case}/{par_dirB}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsA.solver_parFile}' '{dest_case}/{spar_dirA}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsB.solver_parFile}' '{dest_case}/{spar_dirB}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsA.network_parFile}' '{dest_case}/{npar_dirA}'"
#         f" && ln -s '{p}{p}{bc}/{dwo_pathsB.network_parFile}' '{dest_case}/{npar_dirB}'"
#         f" && cp '{bc}/{dwo_pathsA.dydFile_contg}' '{dest_case}/{contg_dyd_dirA}'"
#         f" && cp '{bc}/{dwo_pathsA.parFile_contg}' '{dest_case}/{contg_par_dirA}'"
#         f" && cp '{bc}/{dwo_pathsB.dydFile_contg}' '{dest_case}/{contg_dyd_dirB}'"
#         f" && cp '{bc}/{dwo_pathsB.parFile_contg}' '{dest_case}/{contg_par_dirB}'"
#         + copy_diagr_commandA
#         + copy_diagr_commandB
#     )
#     try:
#         retcode = subprocess.call(full_command, shell=True)
#         if retcode < 0:
#             raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
#         elif retcode > 0:
#             raise ValueError("Copy operation returned error code: %d" % retcode)
#     except OSError as e:
#         print("Copy operation failed: ", e, file=sys.stderr)
#         raise
#
#
# def clone_base_case(input_case, dest_case):
#     # If the destination exists, remove it (it's temporary anyway)
#     if os.path.exists(dest_case):
#         remove_case(dest_case)
#
#     try:
#         retcode = subprocess.call(
#             "rsync -aq --exclude 't0/' '%s/' '%s'" % (input_case, dest_case), shell=True
#         )
#         if retcode < 0:
#             raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
#         elif retcode > 0:
#             raise ValueError("Copy operation returned error code: %d" % retcode)
#     except OSError as e:
#         print("Copy operation failed: ", e, file=sys.stderr)
#         raise


def remove_case(dest_case):
    try:
        retcode = subprocess.call("rm -rf '%s'" % dest_case, shell=True)
        if retcode < 0:
            raise ValueError("rm of bad case was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("rm of bad case returned error code: %d" % retcode)
    except OSError as e:
        print("call to rm failed: ", e, file=sys.stderr)
        raise


def parse_basecase(base_case, hades_file, olf_file):
    Parsed_case = namedtuple(
        "Parsed_case",
        "hades_tree olf_tree",
    )

    hades_tree = etree.parse(
        os.path.join(base_case, hades_file), etree.XMLParser(remove_blank_text=True)
    )

    olf_tree = etree.parse(
        os.path.join(base_case, olf_file),
        etree.XMLParser(remove_blank_text=True),
    )

    return Parsed_case(
        hades_tree=hades_tree,
        olf_tree=olf_tree,
    )


#
# def calc_global_score(df, W_V, W_P, W_Q, W_T, MAX_THRESH, MEAN_THRESH, P95_THRESH):
#     df_all = df.loc[(df.volt_level == "ALL")]
#     name_score = list(df_all["contg_case"])
#     score_max = []
#     score_mean = []
#     score_p95 = []
#     max_n_pass = 0
#     mean_n_pass = 0
#     p95_n_pass = 0
#     total_n_pass = len(df_all.index)
#
#     for i in range(len(df_all.index)):
#         max_val = (
#             abs(df_all.iloc[i, 3]) * W_P
#             + abs((df_all.iloc[i, 4] * 0.5 + df_all.iloc[i, 5] * 0.5)) * W_P
#             + abs(df_all.iloc[i, 6]) * W_T
#             + abs(df_all.iloc[i, 7]) * W_Q
#             + abs((df_all.iloc[i, 8] * 0.5 + df_all.iloc[i, 9] * 0.5)) * W_Q
#             + abs(df_all.iloc[i, 10]) * W_T
#             + abs(df_all.iloc[i, 11]) * W_V
#         )
#         if max_val > MAX_THRESH:
#             max_n_pass += 1
#
#         score_max.append(max_val)
#
#         p95_val = (
#             abs(df_all.iloc[i, 13]) * W_P
#             + abs((df_all.iloc[i, 14] * 0.5 + df_all.iloc[i, 15] * 0.5)) * W_P
#             + abs(df_all.iloc[i, 16]) * W_T
#             + abs(df_all.iloc[i, 17]) * W_Q
#             + abs((df_all.iloc[i, 18] * 0.5 + df_all.iloc[i, 19] * 0.5)) * W_Q
#             + abs(df_all.iloc[i, 20]) * W_T
#             + abs(df_all.iloc[i, 21]) * W_V
#         )
#         if p95_val > P95_THRESH:
#             p95_n_pass += 1
#         score_p95.append(p95_val)
#
#         mean_val = (
#             abs(df_all.iloc[i, 23]) * W_P
#             + abs((df_all.iloc[i, 24] * 0.5 + df_all.iloc[i, 25] * 0.5)) * W_P
#             + abs(df_all.iloc[i, 26]) * W_T
#             + abs(df_all.iloc[i, 27]) * W_Q
#             + abs((df_all.iloc[i, 28] * 0.5 + df_all.iloc[i, 29] * 0.5)) * W_Q
#             + abs(df_all.iloc[i, 30]) * W_T
#             + abs(df_all.iloc[i, 31]) * W_V
#         )
#         if mean_val > MEAN_THRESH:
#             mean_n_pass += 1
#         score_mean.append(mean_val)
#
#     dict_score = {
#         "CONTG": name_score,
#         "MAX_SCORE": score_max,
#         "P95_SCORE": score_p95,
#         "MEAN_SCORE": score_mean,
#     }
#     df_score = pd.DataFrame(dict_score)
#     df_score = df_score.sort_values("MAX_SCORE", axis=0, ascending=False)
#
#     return df_score, max_n_pass, p95_n_pass, mean_n_pass, total_n_pass
