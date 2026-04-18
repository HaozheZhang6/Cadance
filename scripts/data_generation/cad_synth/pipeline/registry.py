"""Family registry — maps family names to BaseFamily instances."""

from ..families.ball_knob import BallKnobFamily
from ..families.base import BaseFamily
from ..families.circlip import CirclipFamily
from ..families.dowel_pin import DowelPinFamily
from ..families.plain_washer import WasherFamily
from ..families.sprocket import SprocketFamily
from ..families.cruciform import CruciformFamily
from ..families.dog_bone import DogBoneFamily
from ..families.flat_link import FlatLinkFamily
from ..families.ratchet_sector import RatchetSectorFamily
from ..families.rect_frame import RectFrameFamily
from ..families.star_blank import StarBlankFamily
from ..families.bolt import BoltFamily
from ..families.bucket import BucketFamily
from ..families.chair import ChairFamily
from ..families.clevis import ClevisFamily
from ..families.fan_shroud import FanShroudFamily
from ..families.handwheel import HandwheelFamily
from ..families.hex_nut import HexNutFamily
from ..families.mesh_panel import MeshPanelFamily
from ..families.mounting_angle import MountingAngleFamily
from ..families.nozzle import NozzleFamily
from ..families.snap_clip import SnapClipFamily
from ..families.table import TableFamily
from ..families.wire_grid import WireGridFamily
from ..families.bearing_retainer_cap import BearingRetainerCapFamily
from ..families.bellows import BellowsFamily
from ..families.bevel_gear import BevelGearFamily
from ..families.cable_routing_panel import CableRoutingPanelFamily
from ..families.cam import CamFamily
from ..families.capsule import CapsuleFamily
from ..families.coil_spring import CoilSpringFamily
from ..families.connecting_rod import ConnectingRodFamily
from ..families.connector_faceplate import ConnectorFaceplateFamily
from ..families.dome_cap import DomeCapFamily
from ..families.dovetail_slide import DovetailSlideFamily
from ..families.duct_elbow import DuctElbowFamily
from ..families.enclosure import EnclosureFamily
from ..families.gusseted_bracket import GussetedBracketFamily
from ..families.heat_sink import HeatSinkFamily
from ..families.helical_gear import HelicalGearFamily
from ..families.hex_standoff import HexStandoffFamily
from ..families.hinge import HingeFamily
from ..families.hollow_tube import HollowTubeFamily
from ..families.i_beam import IBeamFamily
from ..families.impeller import ImpellerFamily
from ..families.knob import KnobFamily
from ..families.l_bracket import LBracketFamily
from ..families.lathe_turned_part import LatheTurnedPartFamily
from ..families.locator_block import LocatorBlockFamily
from ..families.manifold_block import ManifoldBlockFamily
from ..families.motor_end_cap import MotorEndCapFamily
from ..families.mounting_plate import MountingPlateFamily
from ..families.pcb_standoff_plate import PcbStandoffPlateFamily
from ..families.pipe_elbow import PipeElbowFamily
from ..families.pipe_flange import PipeFlangeFamily
from ..families.piston import PistonFamily
from ..families.propeller import PropellerFamily
from ..families.pulley import PulleyFamily
from ..families.rib_plate import RibPlateFamily
from ..families.round_flange import RoundFlangeFamily
from ..families.shaft_collar import ShaftCollarFamily
from ..families.sheet_metal_tray import SheetMetalTrayFamily
from ..families.slotted_plate import SlottedPlateFamily
from ..families.spacer_ring import SpacerRingFamily
from ..families.spur_gear import SpurGearFamily
from ..families.standoff import StandoffFamily
from ..families.stepped_shaft import SteppedShaftFamily
from ..families.t_pipe_fitting import TPipeFittingFamily
from ..families.t_slot_rail import TSlotRailFamily
from ..families.tapered_boss import TaperedBossFamily
from ..families.threaded_adapter import ThreadedAdapterFamily
from ..families.torus_link import TorusLinkFamily
from ..families.u_channel import UChannelFamily
from ..families.vented_panel import VentedPanelFamily
from ..families.waffle_plate import WafflePlateFamily
from ..families.worm_screw import WormScrewFamily
from ..families.z_bracket import ZBracketFamily
from ..families.parallel_key import ParallelKeyFamily
from ..families.clevis_pin import ClevisPinFamily
from ..families.taper_pin import TaperPinFamily

_FAMILIES: dict[str, BaseFamily] = {}


def _register_builtins():
    """Register built-in families."""
    for cls in [
        MountingPlateFamily,
        RoundFlangeFamily,
        LBracketFamily,
        EnclosureFamily,
        HollowTubeFamily,
        VentedPanelFamily,
        SteppedShaftFamily,
        HeatSinkFamily,
        PipeFlangeFamily,
        UChannelFamily,
        StandoffFamily,
        SlottedPlateFamily,
        BearingRetainerCapFamily,
        ShaftCollarFamily,
        ConnectorFaceplateFamily,
        MotorEndCapFamily,
        PcbStandoffPlateFamily,
        CableRoutingPanelFamily,
        LocatorBlockFamily,
        GussetedBracketFamily,
        SpacerRingFamily,
        LatheTurnedPartFamily,
        TSlotRailFamily,
        RibPlateFamily,
        HexStandoffFamily,
        TaperedBossFamily,
        IBeamFamily,
        WafflePlateFamily,
        CoilSpringFamily,
        PipeElbowFamily,
        HingeFamily,
        SpurGearFamily,
        ImpellerFamily,
        PulleyFamily,
        KnobFamily,
        DovetailSlideFamily,
        CamFamily,
        SheetMetalTrayFamily,
        WormScrewFamily,
        ThreadedAdapterFamily,
        ZBracketFamily,
        TPipeFittingFamily,
        BellowsFamily,
        ManifoldBlockFamily,
        ConnectingRodFamily,
        HelicalGearFamily,
        PropellerFamily,
        BevelGearFamily,
        DomeCapFamily,
        CapsuleFamily,
        TorusLinkFamily,
        PistonFamily,
        DuctElbowFamily,
        BallKnobFamily,
        BoltFamily,
        BucketFamily,
        ChairFamily,
        ClevisFamily,
        FanShroudFamily,
        HandwheelFamily,
        HexNutFamily,
        MeshPanelFamily,
        MountingAngleFamily,
        NozzleFamily,
        SnapClipFamily,
        TableFamily,
        WireGridFamily,
        FlatLinkFamily,
        RatchetSectorFamily,
        CruciformFamily,
        DogBoneFamily,
        RectFrameFamily,
        StarBlankFamily,
        CirclipFamily,
        DowelPinFamily,
        SprocketFamily,
        WasherFamily,
        ParallelKeyFamily,
        ClevisPinFamily,
        TaperPinFamily,
    ]:
        _FAMILIES[cls.name] = cls()


_register_builtins()


def get_family(name: str) -> BaseFamily:
    """Return family instance by name."""
    if name not in _FAMILIES:
        raise KeyError(f"Unknown family: {name}. Available: {list(_FAMILIES)}")
    return _FAMILIES[name]


def list_families() -> list[str]:
    """Return sorted list of registered family names."""
    return sorted(_FAMILIES.keys())


def register_family(family: BaseFamily):
    """Register a custom family instance."""
    _FAMILIES[family.name] = family
