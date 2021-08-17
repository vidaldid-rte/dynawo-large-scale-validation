

The attic
=========

The place where we put away junk that could be useful again some day.

  * `bus_contingencies.py`: this was written with the aim of comparing
    bus contingencies in Astre vs. Dynawo. As such, it was designed to
    be restricted to BUS BREAKER topology buses, since NODE BREAKER
    busbarSections cannot be easily matched to Astre buses. The
    problem is, it turns out that Dynawo only allows to configure bus
    disconnections for NODE BREAKER busbars!!! (we didn't know this)
    -- Nevertheless, we keep this script here because it'll be useful
    for the dwodwo pipeline: just modify it to consider only NODE
    BREAKER buses.

  * `load_contingencies_identByBus.py`: this was an attempt to
     sidestep the problems brought about by Dynawo RTE cases in which
     many (most) loads have been merged. Such loads cannot be matched
     to the loads in the corresponding Astre case, because they are
     kept unmerged in Astre. So here we tried a strategy consisting in
     disconnecting ALL the loads at the same bus.  But then we hit an
     unexpected problem: Astre seems to have a bug, it doesn't really
     disconnect all the loads (it only disconnects one). So we
     abandoned this script. We fell back on the standard script, which
     tries to match loads one-to-one (there are still many useful
     matches anyway).
     
  * `gcompare.ipynb`, `sparklines.py`: this was an early experiment, a
    simple test of "sparklines" as a quick visual way to compare
    results qualitatively. It didn't prove very useful.
    
  * `Compare_solutions.ipynb`: first version of the contingency 
  comparison file.

