"""Family registry — maps family names to BaseFamily instances."""

from ..families.ball_knob import BallKnobFamily
from ..families.base import BaseFamily
from ..families.bearing_retainer_cap import BearingRetainerCapFamily
from ..families.battery_holder import BatteryHolderFamily
from ..families.bellows import BellowsFamily
from ..families.bevel_gear import BevelGearFamily
from ..families.bolt import BoltFamily
from ..families.bucket import BucketFamily
from ..families.cable_routing_panel import CableRoutingPanelFamily
from ..families.cam import CamFamily
from ..families.capsule import CapsuleFamily
from ..families.chair import ChairFamily
from ..families.circlip import CirclipFamily
from ..families.clevis import ClevisFamily
from ..families.clevis_pin import ClevisPinFamily
from ..families.coil_spring import CoilSpringFamily
from ..families.connecting_rod import ConnectingRodFamily
from ..families.connector_faceplate import ConnectorFaceplateFamily
from ..families.cotter_pin import CotterPinFamily
from ..families.cruciform import CruciformFamily
from ..families.dog_bone import DogBoneFamily
from ..families.dome_cap import DomeCapFamily
from ..families.double_simplex_sprocket import DoubleSimplexSprocketFamily
from ..families.dovetail_slide import DovetailSlideFamily
from ..families.dowel_pin import DowelPinFamily
from ..families.duct_elbow import DuctElbowFamily
from ..families.enclosure import EnclosureFamily
from ..families.eyebolt import EyeboltFamily
from ..families.fan_shroud import FanShroudFamily
from ..families.flat_link import FlatLinkFamily
from ..families.grease_nipple import GreaseNippleFamily
from ..families.gridfinity_bin import GridfinityBinFamily
from ..families.grommet import GrommetFamily
from ..families.gusseted_bracket import GussetedBracketFamily
from ..families.handwheel import HandwheelFamily
from ..families.heat_sink import HeatSinkFamily
from ..families.helical_gear import HelicalGearFamily
from ..families.hex_key_organizer import HexKeyOrganizerFamily
from ..families.hex_nut import HexNutFamily
from ..families.hex_standoff import HexStandoffFamily
from ..families.hinge import HingeFamily
from ..families.hollow_tube import HollowTubeFamily
from ..families.i_beam import IBeamFamily
from ..families.impeller import ImpellerFamily
from ..families.j_hook import JHookFamily
from ..families.keyhole_plate import KeyholePlateFamily
from ..families.knob import KnobFamily
from ..families.l_bracket import LBracketFamily
from ..families.lathe_turned_part import LatheTurnedPartFamily
from ..families.lobed_knob import LobedKnobFamily
from ..families.locator_block import LocatorBlockFamily
from ..families.manifold_block import ManifoldBlockFamily
from ..families.mesh_panel import MeshPanelFamily
from ..families.motor_end_cap import MotorEndCapFamily
from ..families.mounting_angle import MountingAngleFamily
from ..families.mounting_plate import MountingPlateFamily
from ..families.nozzle import NozzleFamily
from ..families.pan_head_screw import PanHeadScrewFamily
from ..families.parallel_key import ParallelKeyFamily
from ..families.pcb_standoff_plate import PcbStandoffPlateFamily
from ..families.phone_stand import PhoneStandFamily
from ..families.pillow_block import PillowBlockFamily
from ..families.pipe_elbow import PipeElbowFamily
from ..families.pipe_flange import PipeFlangeFamily
from ..families.piston import PistonFamily
from ..families.plain_washer import WasherFamily
from ..families.propeller import PropellerFamily
from ..families.pull_handle import PullHandleFamily
from ..families.pulley import PulleyFamily
from ..families.ratchet_sector import RatchetSectorFamily
from ..families.rect_frame import RectFrameFamily
from ..families.rib_plate import RibPlateFamily
from ..families.rivet import RivetFamily
from ..families.round_flange import RoundFlangeFamily
from ..families.shaft_collar import ShaftCollarFamily
from ..families.sheet_metal_tray import SheetMetalTrayFamily
from ..families.slotted_plate import SlottedPlateFamily
from ..families.snap_clip import SnapClipFamily
from ..families.spacer_ring import SpacerRingFamily
from ..families.spline_hub import SplineHubFamily
from ..families.sprocket import SprocketFamily
from ..families.spur_gear import SpurGearFamily
from ..families.standoff import StandoffFamily
from ..families.star_blank import StarBlankFamily
from ..families.stepped_shaft import SteppedShaftFamily
from ..families.t_pipe_fitting import TPipeFittingFamily
from ..families.t_slot_rail import TSlotRailFamily
from ..families.table import TableFamily
from ..families.taper_pin import TaperPinFamily
from ..families.tapered_boss import TaperedBossFamily
from ..families.tee_nut import TeeNutFamily
from ..families.threaded_adapter import ThreadedAdapterFamily
from ..families.torsion_spring import TorsionSpringFamily
from ..families.torus_link import TorusLinkFamily
from ..families.turnbuckle import TurnbuckleFamily
from ..families.twisted_bracket import TwistedBracketFamily
from ..families.twisted_drill import TwistedDrillFamily
from ..families.u_bolt import UBoltFamily
from ..families.u_channel import UChannelFamily
from ..families.vented_panel import VentedPanelFamily
from ..families.venturi_tube import VenturiTubeFamily
from ..families.waffle_plate import WafflePlateFamily
from ..families.wall_anchor import WallAnchorFamily
from ..families.wing_nut import WingNutFamily
from ..families.wire_grid import WireGridFamily
from ..families.worm_screw import WormScrewFamily
from ..families.z_bracket import ZBracketFamily

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
        DoubleSimplexSprocketFamily,
        WasherFamily,
        ParallelKeyFamily,
        ClevisPinFamily,
        TaperPinFamily,
        TorsionSpringFamily,
        EyeboltFamily,
        SplineHubFamily,
        VenturiTubeFamily,
        TwistedBracketFamily,
        TwistedDrillFamily,
        WingNutFamily,
        LobedKnobFamily,
        GreaseNippleFamily,
        UBoltFamily,
        RivetFamily,
        CotterPinFamily,
        PullHandleFamily,
        PillowBlockFamily,
        TurnbuckleFamily,
        KeyholePlateFamily,
        PanHeadScrewFamily,
        GrommetFamily,
        TeeNutFamily,
        JHookFamily,
        WallAnchorFamily,
        GridfinityBinFamily,
        HexKeyOrganizerFamily,
        BatteryHolderFamily,
        PhoneStandFamily,
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
