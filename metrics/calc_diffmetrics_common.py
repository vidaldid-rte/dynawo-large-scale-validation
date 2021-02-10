# Common functions for the diffmetrics scripts
from lxml import etree


def get_time_params(base_case, verbose):
    # Obtain the simulation start and end times from Dynawo's JOB file.
    job_file = base_case + "/fic_JOB.xml"
    tree = etree.parse(job_file)
    root = tree.getroot()
    last_job = root[-1]
    simulation = last_job.find("simulation", root.nsmap)
    startTime = float(simulation.get("startTime"))
    stopTime = float(simulation.get("stopTime"))
    # Obtain the time at which the contingency takes place.
    # We base our search on Dynawo's DYD file, relying on a "Disconnect" string
    dyd_file = base_case + "/tFin/fic_DYD.xml"
    tree = etree.parse(dyd_file)
    root = tree.getroot()
    parId = None
    for bbm in root.iterfind("./blackBoxModel", root.nsmap):
        if "Disconnect" in bbm.get("id"):
            parId = bbm.get("parId")
            break
    par_file = base_case + "/tFin/fic_PAR.xml"
    tree = etree.parse(par_file)
    root = tree.getroot()
    for parset in root.iterfind("./set", root.nsmap):
        if parset.get("id") == parId:
            for par in parset:
                if par.get("name") == "event_tEvent":
                    event_tEvent = float(par.get("value"))
                    break
            break

    if verbose:
        print(
            "startTime, stopTime, event_tEvent: %f, %f, %f"
            % (startTime, stopTime, event_tEvent)
        )

    return startTime, stopTime, event_tEvent
