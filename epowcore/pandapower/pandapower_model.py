"""pandapower_model module providing the PandapowerModel class used to create
the converted pandapower network.
"""

from dataclasses import dataclass
from math import pi

import pandapower
from numpy import nan

from epowcore.gdf.bus import Bus, BusType, LFBusType
from epowcore.gdf.component import Component
from epowcore.gdf.core_model import CoreModel
from epowcore.gdf.generators.synchronous_machine import SynchronousMachine
from epowcore.gdf.load import Load
from epowcore.gdf.shunt import Shunt
from epowcore.gdf.switch import Switch
from epowcore.gdf.tline import TLine
from epowcore.gdf.transformers.three_winding_transformer import ThreeWindingTransformer
from epowcore.gdf.transformers.two_winding_transformer import TwoWindingTransformer
from epowcore.gdf.utils import get_connected_bus
from epowcore.gdf.ward import Ward
from epowcore.generic.constants import Platform
from epowcore.generic.logger import Logger


@dataclass(kw_only=True)
class PandapowerModel:
    """Wrapper class around a Pandapower Network,
    with functions that take a gdf component of a kind and create a
    equivalent component in the pandapower network.
    """

    network: pandapower.pandapowerNet
    platform: Platform

    def create_bus_from_gdf(self, bus: Bus):
        """Create a pandapower bus in the PandapowerModel Network
        from a given gdf bus.
        """
        pandapower_type = "b"
        if Bus.bus_type == BusType.JUNCTION:
            pandapower_type = "n"
        # Creating the bus in the Pandapower Network
        pandapower.create_bus(
            net=self.network,
            name=bus.name,
            index=bus.uid,
            geodata=bus.coords,
            coords=bus.coords,
            vn_kv=bus.nominal_voltage,
            type=pandapower_type,
            zone=None,
            in_service=True,
            max_vm_pu=nan,
            min_vm_pu=nan,
        )

    def create_load_from_gdf(self, core_model: CoreModel, load: Load) -> bool:
        """Create a pandapower load in the PandapowerModel Network from a
        load in the CoreModel.
        """
        # Getting load bus
        load_bus = get_connected_bus(core_model.graph, load, max_depth=1)
        # If no load bus was found the function fails
        if load_bus is None:
            Logger.log_to_selected("Their was no bus found connected to the load")
            return False
        # Create the pandapower load in the network
        pandapower.create_load(
            net=self.network,
            name=load.name,
            index=load.uid,
            bus=load_bus.uid,
            p_mw=load.active_power,
            q_mvar=load.reactive_power,
            const_z_percent=0,
            const_i_percent=0,
            sn_mva=nan,
            scaling=1.0,
            in_service=True,
            type="wye",
            max_p_mw=nan,
            min_p_mw=nan,
            max_q_mvar=nan,
            min_q_mvar=nan,
            controllable=nan,
        )
        return True

    def create_two_winding_transformer_from_gdf(
        self, core_model: CoreModel, transformer: TwoWindingTransformer
    ):
        """Create two winding pandapower transformer based on a given
        two winding transformer from gdf and add it into the network.
        """
        # Get the bus connected to the transformer on the high voltage side
        high_voltage_bus = core_model.get_neighbors(
            component=transformer, follow_links=True, connector="HV"
        )[0]
        # Get the bus connected to the transformer on the low voltage side
        low_voltage_bus = core_model.get_neighbors(
            component=transformer, follow_links=True, connector="LV"
        )[0]
        # If either bus wasnt found the function failed
        if high_voltage_bus is None or low_voltage_bus is None:
            Logger.log_to_selected("Failled to convert two winding transformer")
            return False
        # Set vk_percent to a default value if r1pu is zero
        if transformer.r1pu != 0:
            vk_percent = transformer.r1pu * (transformer.voltage_hv / transformer.voltage_lv) * 100
        else:
            vk_percent = transformer.get_default(attr="vk_percent", platform=self.platform)
        # Create transformer in pandapower network
        pandapower.create_transformer_from_parameters(
            net=self.network,
            name=transformer.name,
            index=transformer.uid,
            hv_bus=high_voltage_bus.uid,
            lv_bus=low_voltage_bus.uid,
            sn_mva=transformer.rating,
            vn_hv_kv=transformer.voltage_hv,
            vn_lv_kv=transformer.voltage_lv,
            vkr_percent=0,
            vk_percent=vk_percent,
            pfe_kw=transformer.pfe_kw,
            i0_percent=0,
            shift_degree=transformer.phase_shift_30 * 30,
            tap_side="hv",
            tap_neutral=transformer.tap_neutral,
            tap_max=transformer.tap_max,
            tap_min=transformer.tap_min,
            tap_step_percent=transformer.tap_changer_voltage * 100,
            tap_step_degree=nan,
            tap_pos=transformer.tap_initial,
            tap_phase_shifter=False,
            tap_set_vm_pu=transformer.get_default(attr="tap_set_vm_pu", platform=self.platform),
            in_service=True,
            vector_group=None,
            max_loading_percent=nan,
            parallel=1,
            df=1.0,
            vk0_percent=nan,
            vkr0_percent=nan,
            mag0_percent=transformer.get_default(attr="mag0_percent", platform=self.platform),
            mag0_rx=transformer.get_default(attr="mag0_rx", platform=self.platform),
            si0_hv_partial=transformer.get_default(attr="si0_hv_partial", platform=self.platform),
            pt_percent=nan,
            oltc=nan,
            tap_dependent_impedance=nan,
            vk_percent_characteristic=None,
            vkr_percent_characteristic=None,
            xn_ohm=nan,
            tap2_side=None,
            tap2_neutral=nan,
            tap2_max=nan,
            tap2_min=nan,
            tap2_step_percent=nan,
            tap2_step_degree=nan,
            tap2_pos=nan,
            tap2_phase_shifter=nan,
        )
        return True

    def create_three_winding_transformer_from_gdf(
        self, core_model: CoreModel, transformer3w: ThreeWindingTransformer
    ):
        """Create thee winding pandapower transformer based on a given
        three winding transformer from gdf and add it into the network.
        """
        # Get the bus connected to the transformer on the high voltage side
        high_voltage_bus = core_model.get_neighbors(
            component=transformer3w, follow_links=True, connector="HV"
        )[0]
        # Get the bus connected to the transformer on the middle voltage side
        middle_voltage_bus = core_model.get_neighbors(
            component=transformer3w, follow_links=True, connector="MV"
        )
        # Get the bus connected to the transformer on the low voltage side
        low_voltage_bus = core_model.get_neighbors(
            component=transformer3w, follow_links=True, connector="LV"
        )[0]
        # If either bus wasnt found the function failed
        if high_voltage_bus is None or low_voltage_bus is None or middle_voltage_bus is None:
            Logger.log_to_selected("Failled to convert three winding transformer")
            return False
        # Create transformer in pandapower network
        pandapower.create.create_transformer3w_from_parameters(
            net=self.network,
            name=transformer3w.name,
            index=transformer3w.uid,
            hv_bus=high_voltage_bus.uid,
            mv_bus=middle_voltage_bus.uid,
            lv_bus=low_voltage_bus.uid,
            vn_hv_kv=transformer3w.voltage_hv,
            vn_mv_kv=transformer3w.voltage_mv,
            vn_lv_kv=transformer3w.voltage_lv,
            sn_hv_mva=transformer3w.rating_hv,
            sn_mv_mva=transformer3w.rating_mv,
            sn_lv_mva=transformer3w.rating_lv,
            vk_hv_percent=10.4,
            vk_mv_percent=10.4,
            vk_lv_percent=10.4,
            vkr_hv_percent=0.28,
            vkr_mv_percent=0.32,
            vkr_lv_percent=0.35,
            pfe_kw=transformer3w.pfe_kw,
            i0_percent=0.89,
            shift_mv_degree=transformer3w.phase_shift_30_mv * 30,
            shift_lv_degree=transformer3w.phase_shift_30_lv * 30,
            tap_side="hv",
            tap_step_percent=transformer3w.TapDetails.tap_changer_voltage * 100,
            tap_step_degree=nan,
            tap_pos=transformer3w.TapDetails.tap_initial,
            tap_neutral=transformer3w.TapDetails.tap_neutral,
            tap_max=transformer3w.TapDetails.tap_max,
            tap_min=transformer3w.TapDetails.tap_min,
            in_service=True,
            max_loading_percent=nan,
            tap_at_star_point=False,
            vk0_hv_percent=nan,
            vk0_mv_percent=nan,
            vk0_lv_percent=nan,
            vkr0_hv_percent=nan,
            vkr0_mv_percent=nan,
            vkr0_lv_percent=nan,
            vector_group=None,
            tap_dependent_impedance=nan,
            vk_hv_percent_characteristic=None,
            vkr_hv_percent_characteristic=None,
            vk_mv_percent_characteristic=None,
            vkr_mv_percent_characteristic=None,
            vk_lv_percent_characteristic=None,
            vkr_lv_percent_characteristic=None,
        )
        return True

    def create_generator_from_gdf_synchronous_maschine(
        self, core_model: CoreModel, synchronous_maschine: SynchronousMachine
    ):
        """Create a generator in the pandapower network equivalent to
        the given synchronous_maschine in gdf format.
        """
        # Getting the bus the generator is connected to
        synchronous_maschine_bus = get_connected_bus(
            core_model.graph, synchronous_maschine, max_depth=1
        )
        # If the bus wasnt found the function fails
        if synchronous_maschine_bus is None:
            Logger.log_to_selected("Failed to convert synchonous_maschine")
            return False

        # Check if the generator bus was slack
        slack = False
        if synchronous_maschine_bus.lf_bus_type == LFBusType("SLACK"):
            slack = True
            Logger.log_to_selected(
                "Gen:" + synchronous_maschine.name + " is set to be a slack genenerator"
            )
        # Create generator in pandapower network
        pandapower.create_gen(
            net=self.network,
            name=synchronous_maschine.name,
            index=synchronous_maschine.uid,
            bus=synchronous_maschine_bus.uid,
            p_mw=synchronous_maschine.active_power,
            vm_pu=synchronous_maschine.voltage_set_point,
            sn_mva=synchronous_maschine.rated_apparent_power,
            max_q_mvar=synchronous_maschine.q_max,
            min_q_mvar=synchronous_maschine.q_min,
            min_p_mw=synchronous_maschine.p_min,
            max_p_mw=synchronous_maschine.p_max,
            min_vm_pu=nan,
            max_vm_pu=nan,
            scaling=1.0,
            type="sync",
            slack=slack,
            controllable=False,
            vn_kv=synchronous_maschine.rated_voltage,
            xdss_pu=synchronous_maschine.subtransient_reactance_x,
            rdss_ohm=nan,
            cos_phi=nan,
            pg_percent=nan,
            power_station_trafo=nan,
            in_service=True,
            slack_weight=0.0,
        )
        return True

    def create_line_from_gdf_tline(self, core_model: CoreModel, tline: TLine):
        """Create a pandapower line in the network equivalent to a gdf transmission line"""
        # Get the neigbours of the transmission line to know what it connects to
        from_bus = core_model.get_neighbors(component=tline, follow_links=True, connector="A")[0]
        to_bus = core_model.get_neighbors(component=tline, follow_links=True, connector="B")[0]
        # Conversion fails if one of the buses isn't found
        if from_bus is None or to_bus is None:
            print("Conversion of " + tline.name + " failed")
            return False
        network_frequency = core_model.base_frequency
        # Create line in pandapower network
        pandapower.create_line_from_parameters(
            net=self.network,
            name=tline.name,
            index=tline.uid,
            geodata=tline.coords,
            from_bus=from_bus.uid,
            to_bus=to_bus.uid,
            length_km=tline.length,
            r_ohm_per_km=tline.r1,
            x_ohm_per_km=tline.x1,
            c_nf_per_km=(tline.b1 * 1e3) / (2 * pi * network_frequency),
            max_i_ka=0.5,
            type=None,
            in_service=True,
            df=1.0,
            parallel=tline.parallel_lines,
            g_us_per_km=0.0,
            max_loading_percent=nan,
            alpha=tline.get_default(attr="alpha", platform=self.platform),
            temperature_degree_celsius=tline.get_default(
                attr="temperature_degree_celsius", platform=self.platform
            ),
            r0_ohm_per_km=tline.r0_fb(platform=self.platform),
            x0_ohm_per_km=tline.x0_fb(platform=self.platform),
            c0_nf_per_km=nan,
            g0_us_per_km=0,
            endtemp_degree=nan,
        )
        return True

    def create_ward_from_gdf_ward(self, core_model: CoreModel, ward: Ward):
        """Creates a ward in the pandapower network equivalent to a given
        ward from the gdf.
        """
        ward_bus = get_connected_bus(core_model.graph, ward, max_depth=1)
        # If there was no ward_bus found the function failed and terminates
        if ward_bus is None:
            return False
        # Create ward in pandapower network
        pandapower.create_ward(
            net=self.network,
            name=ward.name,
            index=ward.uid,
            bus=ward_bus,
            ps_mw=-ward.p_gen + ward.p_load,
            qs_mvar=-ward.q_gen + ward.q_load,
            pz_mw=ward.p_zload,
            qz_mvar=ward.q_zload,
            in_service=True,
        )
        return True

    def create_shunt_from_gdf_shunt(self, core_model: CoreModel, shunt: Shunt):
        """Creates a shunt in the pandapower network equivalent to a given
        shunt from gdf.
        """
        shunt_bus = get_connected_bus(core_model.graph, shunt, max_depth=1)
        # If there was no shunt_bus found the function failed and terminates
        if shunt_bus is None:
            return False
        # Create shunt in pandapower network
        pandapower.create_shunt(
            net=self.network,
            index=shunt.uid,
            bus=shunt_bus,
            p_mw=shunt.p,
            q_mvar=shunt.q,
        )
        return True

    def _create_pandapower_switch_et(self, component: Component) -> str | bool:
        """Returns the right value for the et variable of the pandapower switch
        based on the given gdf component.
        """
        match component:
            case Bus():
                return "b"
            case TLine():
                return "I"
            case TwoWindingTransformer():
                return "t"
            case ThreeWindingTransformer():
                return "t3"
            case _:
                return False

    def create_switch_from_gdf_switch(self, core_model: CoreModel, switch: Switch):
        """Create a pandapower switch in the network from a given
        gdf switch.
        """
        neighbours = core_model.get_neighbors(component=switch, follow_links=True, connector=None)
        # If there are less than two neighbours found the function fails
        if len(neighbours) == 2:
            if isinstance(neighbours[0], Bus):
                switch_bus = neighbours[0].uid
                switch_other_component = neighbours[1].uid
            else:
                switch_bus = neighbours[1].uid
                switch_other_component = neighbours[0].uid
        else:
            return False
        # Get string mapped to the type of the other component
        switch_et = self._create_pandapower_switch_et(switch_other_component)
        # If it wasn't possible to map the component the function fails
        if not switch_et:
            Logger.log_to_selected(
                "Failed to convert " + switch.name + " because of the connected components"
            )
            return False
        voltage = switch_bus.nominal_voltage
        # Create swith in the pandapower network
        pandapower.create_switch(
            net=self.network,
            name=switch.name,
            index=switch.uid,
            bus=switch_bus,
            element=switch_other_component,
            et=switch_et,
            closed=switch.closed,
            in_ka=switch.rating_b * 1000 / voltage,
        )
        return True
