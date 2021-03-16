# Common functions for all contingency-generating scripts
import os
import sys
import subprocess
from lxml import etree
from collections import namedtuple


def check_inputfiles(input_case, dwo_paths, verbose=False):
    if not os.path.isdir(input_case):
        raise ValueError("source directory %s not found" % input_case)

    # remove trailing slash so that basename/dirname below behave consistently:
    if input_case[-1] == "/":
        input_case = input_case[:-1]
    basename = os.path.basename(input_case)
    dirname = os.path.dirname(input_case)
    # corner case: if called from the parent dir, dirname is empty
    if dirname == "":
        dirname = "."

    print("\nUsing input_case: %s" % input_case)
    print("New cases will be generated under: %s" % dirname)
    if verbose:
        print("input_case: %s" % input_case)
        print("basename: %s" % basename)
        print("dirname:  %s" % dirname)

    if not (
        os.path.isfile(input_case + "/Astre/donneesModelesEntree.xml")
        and os.path.isfile(input_case + "/" + dwo_paths.iidmFile)
        and os.path.isfile(input_case + "/" + dwo_paths.dydFile)
        and os.path.isfile(input_case + "/" + dwo_paths.parFile)
        and os.path.isfile(input_case + "/" + dwo_paths.curves_inputFile)
    ):
        raise ValueError("some expected files are missing in %s\n" % input_case)

    return input_case, basename, dirname


def copy_basecase(base_case, dwo_paths, dest_case):
    # If the destination exists, remove it
    if os.path.exists(dest_case):
        remove_case(dest_case)
    # Make the subdirs for Astre and for the Dynawo job; and copy any non-changed
    # files (Dynawo's JOB file and the IIDM) using hard links
    iidm_dir = os.path.dirname(dwo_paths.iidmFile)
    dyd_dir = os.path.dirname(dwo_paths.dydFile)  # all these are usually the same
    par_dir = os.path.dirname(dwo_paths.parFile)  # but we allow themm to be different
    crv_dir = os.path.dirname(dwo_paths.curves_inputFile)  # just in case
    try:
        retcode = subprocess.call(
            f"mkdir -p '{dest_case}/Astre' '{dest_case}/{iidm_dir}'"
            f" '{dest_case}/{dyd_dir}' '{dest_case}/{par_dir}' '{dest_case}/{crv_dir}'"
            f" && cp -l '{dwo_paths.job_file}' '{dest_case}'"
            f" && cp -l '{base_case}/{dwo_paths.iidmFile}' '{dest_case}/{iidm_dir}'",
            shell=True,
        )
        if retcode < 0:
            raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("Copy operation returned error code: %d" % retcode)
    except OSError as e:
        print("Copy operation failed: ", e, file=sys.stderr)
        raise


def clone_base_case(input_case, dest_case):
    # If the destination exists, remove it (it's temporary anyway)
    if os.path.exists(dest_case):
        remove_case(dest_case)

    try:
        retcode = subprocess.call(
            "rsync -aq --exclude 't0/' '%s/' '%s'" % (input_case, dest_case), shell=True
        )
        if retcode < 0:
            raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("Copy operation returned error code: %d" % retcode)
    except OSError as e:
        print("Copy operation failed: ", e, file=sys.stderr)
        raise


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


def dedup_save(basename, edited_case, deduped_case):
    # If the destination exists, warn and rename it to OLD
    if os.path.exists(deduped_case):
        print(
            "   WARNING: destination %s exists! -- renaming it to *__OLD__"
            % deduped_case
        )
        os.rename(deduped_case, deduped_case + "__OLD__")

    # Save it using "deduplication" (actually, hard links)
    dedup_cmd = "rsync -a --delete --link-dest='../%s' '%s/' '%s'" % (
        basename,
        edited_case,
        deduped_case,
    )
    try:
        retcode = subprocess.call(dedup_cmd, shell=True)
        if retcode < 0:
            raise ValueError("Copy operation was terminated by signal: %d" % -retcode)
        elif retcode > 0:
            raise ValueError("Copy operation returned error code: %d" % retcode)
    except OSError as e:
        print("Copy operation failed: ", e, file=sys.stderr)
        raise


def parse_basecase(base_case, dwo_paths, astre_path):
    Parsed_case = namedtuple(
        "Parsed_case", "astreTree iidmTree parTree dydTree crvTree"
    )

    file = base_case + astre_path
    astreTree = etree.parse(file, etree.XMLParser(remove_blank_text=True))

    file = base_case + "/" + dwo_paths.iidmFile
    iidmTree = etree.parse(file, etree.XMLParser(remove_blank_text=True))

    file = base_case + "/" + dwo_paths.parFile
    parTree = etree.parse(file, etree.XMLParser(remove_blank_text=True))

    file = base_case + "/" + dwo_paths.dydFile
    dydTree = etree.parse(file, etree.XMLParser(remove_blank_text=True))

    file = base_case + "/" + dwo_paths.curves_inputFile
    crvTree = etree.parse(file, etree.XMLParser(remove_blank_text=True))

    return Parsed_case(
        astreTree=astreTree,
        iidmTree=iidmTree,
        parTree=parTree,
        dydTree=dydTree,
        crvTree=crvTree,
    )
