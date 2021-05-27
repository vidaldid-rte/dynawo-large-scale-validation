

About HVDC dynamic models in DynaFlow (Quentin Cossart)
=======================================================

The dynamic model currently used^[1] in RTE's DynaFlow cases regulates
the voltage at each terminal of the HVDC link (or only Q, depending on
the parameter modeU) and behaves like an emulated AC line regarding
the active power (we have the equation P = PRef + K * (Theta1f -
Theta2f)). A first order filter is applied to Theta1 and Theta2
(voltage angles at each terminal) to obtain Theta1f and Theta2f, which
means that the active power is not directly at steady state after a
contingency.

In Hades2, the model is the same but without the filtering. It is
considered that the HVDC link reaches its steady state instantaneously
(which is not true in reality).

In Dynawo, if we don't put anything in the .dyd file, the default C++
model only keeps the injections P/Q at the terminals (no AC emulation
and no voltage regulation).



[1] This model makes use of the following components from the library:
      -  lib="HvdcPQPropDiagramPQEmulationVariableK"
      -  lib="VRRemote"
      -  lib="PowerTransferHVDCEmulation"

