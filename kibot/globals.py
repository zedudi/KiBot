# -*- coding: utf-8 -*-
# Copyright (c) 2020-2023 Salvador E. Tropea
# Copyright (c) 2020-2023 Instituto Nacional de Tecnología Industrial
# License: GPL-3.0
# Project: KiBot (formerly KiPlot)
import os
from .error import KiPlotConfigurationError
from .gs import GS
from .optionable import Optionable
from .kicad.config import expand_env
from .macros import macros, document  # noqa: F401
from .pre_filters import FiltersOptions, FilterOptionsKiBot
from .log import get_logger, set_filters
from .misc import W_MUSTBEINT, W_ENVEXIST
from .kicad.config import KiConf
from .kicad.sexpdata import load, SExpData, sexp_iter, Symbol
from .kicad.v6_sch import PCBLayer


class OSVariables(Optionable):
    """ Name/Value pairs """
    def __init__(self):
        super().__init__()
        self._unknown_is_error = True
        with document:
            self.name = ''
            """ *Name of the variable """
            self.value = ''
            """ *Value for the variable """
        self._name_example = 'ROOT_DIR'
        self._value_example = '/root'

    def config(self, parent):
        # Support for - NAME: VALUE
        if len(self._tree) == 1:
            v0 = tuple(self._tree.values())[0]
            n0 = tuple(self._tree.keys())[0]
            if n0 != 'name' and n0 != 'value' and isinstance(v0, str):
                logger.error(self._tree)
                self.name = n0
                self.value = v0
                return
        super().config(parent)
        if not self.name:
            raise KiPlotConfigurationError("Missing or empty `name` in environment variable ({})".format(str(self._tree)))


class Environment(Optionable):
    """ Used to define the KiCad environment vars """
    def __init__(self):
        super().__init__()
        self._unknown_is_error = True
        with document:
            self.symbols = ''
            """ System level symbols dir. KiCad 5: KICAD_SYMBOL_DIR. KiCad 6: KICAD6_SYMBOL_DIR """
            self.footprints = ''
            """ System level footprints (aka modules) dir. KiCad 5: KICAD_FOOTPRINT_DIR and KISYSMOD.
                KiCad 6: KICAD6_FOOTPRINT_DIR """
            self.models_3d = ''
            """ System level 3D models dir. KiCad 5: KISYS3DMOD. KiCad 6: KICAD6_3DMODEL_DIR """
            self.templates = ''
            """ System level templates dir. KiCad 5: KICAD_TEMPLATE_DIR. KiCad 6: KICAD6_TEMPLATE_DIR """
            self.user_templates = ''
            """ User level templates dir. KiCad 5/6: KICAD_USER_TEMPLATE_DIR """
            self.third_party = ''
            """ 3rd party dir. KiCad 6: KICAD6_3RD_PARTY """
            self.define_old = False
            """ Also define legacy versions of the variables.
                Useful when using KiCad 6+ and some libs uses old KiCad 5 names """
            self.extra_os = OSVariables
            """ [list(dict)] Extra variables to export as OS environment variables.
                Note that you can also define them using `- NAME: VALUE` """

    def define_k5_vars(self, defs):
        if self.symbols:
            defs['KICAD_SYMBOL_DIR'] = self.symbols
        if self.footprints:
            defs['KICAD_FOOTPRINT_DIR'] = self.footprints
            defs['KISYSMOD'] = self.footprints
        if self.models_3d:
            defs['KISYS3DMOD'] = self.models_3d
        if self.templates:
            defs['KICAD_TEMPLATE_DIR'] = self.templates
        if self.user_templates:
            defs['KICAD_USER_TEMPLATE_DIR'] = self.user_templates

    def define_k6_vars(self, defs):
        if self.user_templates:
            defs['KICAD_USER_TEMPLATE_DIR'] = self.user_templates
        for n in reversed(range(6, GS.kicad_version_major+1)):
            ki_ver = 'KICAD'+str(n)
            if self.symbols:
                defs[ki_ver+'_SYMBOL_DIR'] = self.symbols
            if self.footprints:
                defs[ki_ver+'_FOOTPRINT_DIR'] = self.footprints
            if self.models_3d:
                defs[ki_ver+'_3DMODEL_DIR'] = self.models_3d
            if self.templates:
                defs[ki_ver+'_TEMPLATE_DIR'] = self.templates
            if self.third_party:
                defs[ki_ver+'_3RD_PARTY'] = self.third_party

    def config(self, parent):
        super().config(parent)
        defs = {}
        if GS.ki5:
            self.define_k5_vars(defs)
        else:
            self.define_k6_vars(defs)
            if self.define_old:
                self.define_k5_vars(defs)
        if len(defs):
            logger.debug('Defining environment vars from the global section')
            env = {}
            if GS.pcb_file:
                env['KIPRJMOD'] = os.path.dirname(GS.pcb_file)
            elif GS.sch_file:
                env['KIPRJMOD'] = os.path.dirname(GS.sch_file)
            for n, v in defs.items():
                v = expand_env(v, env, os.environ)
                logger.debug('- {} = "{}"'.format(n, v))
                os.environ[n] = v
        if isinstance(self.extra_os, list):
            for v in self.extra_os:
                if v.name in os.environ:
                    logger.warning(W_ENVEXIST+"Overwriting {} environment variable".format(v.name))
                logger.debug('- {} = "{}"'.format(v.name, v.value))
                os.environ[v.name] = v.value


class KiCadAlias(Optionable):
    """ KiCad alias (for 3D models) """
    def __init__(self):
        super().__init__()
        self._unknown_is_error = True
        with document:
            self.name = ''
            """ Name of the alias """
            self.variable = None
            """ {name} """
            self.alias = None
            """ {name} """
            self.value = ''
            """ Path to the 3D model """
            self.text = None
            """ {value} """

    def config(self, parent):
        super().config(parent)
        if not self.name:
            raise KiPlotConfigurationError("Missing variable name ({})".format(str(self._tree)))


class Globals(FiltersOptions):
    """ Global options """
    def __init__(self):
        super().__init__()
        with document:
            self.aliases_for_3d_models = KiCadAlias
            """ [list(dict)] List of aliases for the 3D models (KiCad 6).
                KiCad stores 3D aliases with the user settings, not locally.
                This makes impossible to create self contained projects.
                You can define aliases here to workaround this problem.
                The values defined here has precedence over the KiCad configuration.
                Related to https://gitlab.com/kicad/code/kicad/-/issues/3792 """
            self.castellated_pads = False
            """ Has the PCB castellated pads?
                KiCad 6: you should set this in the Board Setup -> Board Finish -> Has castellated pads """
            self.copper_finish = None
            """ {pcb_finish} """
            self.copper_thickness = 35
            """ [number|string] Copper thickness in micrometers (1 Oz is 35 micrometers).
                KiCad 6: you should set this in the Board Setup -> Physical Stackup """
            self.cross_footprints_for_dnp = True
            """ Draw a cross for excluded components in the `Fab` layer """
            self.cross_no_body = False
            """ Cross components even when they don't have a body. Only for KiCad 6 and internal cross """
            self.cross_using_kicad = True
            """ When using KiCad 7+ let KiCad cross the components """
            self.csv_accept_no_ref = False
            """ Accept aggregating CSV files without references (Experimental) """
            self.date_format = '%Y-%m-%d'
            """ Format used for the day we started the script.
                Is also used for the PCB/SCH date formatting when `time_reformat` is enabled (default behavior).
                Uses the `strftime` format """
            self.date_time_format = '%Y-%m-%d_%H-%M-%S'
            """ Format used for the PCB and schematic date when using the file timestamp. Uses the `strftime` format """
            self.dir = ''
            """ Default pattern for the output directories. It also applies to the preflights, unless
                `use_dir_for_preflights` is disabled """
            self.disable_3d_alias_as_env = False
            """ Disable the use of environment and text variables as 3D models aliases """
            self.drc_exclusions_workaround = False
            """ KiCad 6 introduced DRC exclusions. They are stored in the project but ignored by the Python API.
                This is reported as bug number 11562 (https://gitlab.com/kicad/code/kicad/-/issues/11562).
                If you really need exclusions enable this option, this will use the GUI version of the DRC (slower).
                Current KiCad version is 6.0.7 and the bug is still there """
            self.drill_size_increment = 0.05
            """ This is the difference between drill tools in millimeters.
                A manufacturer with 0.05 of increment has drills for 0.1, 0.15, 0.2, 0.25, etc. """
            self.edge_connector = 'no'
            """ [yes,no,bevelled] Has the PCB edge connectors?
                KiCad 6: you should set this in the Board Setup -> Board Finish -> Edge card connectors """
            self.edge_plating = False
            """ Has the PCB a plated board edge?
                KiCad 6: you should set this in the Board Setup -> Board Finish -> Plated board edge """
            self.extra_pth_drill = 0.1
            """ How many millimeters the manufacturer will add to plated holes.
                This is because the plating reduces the hole, so you need to use a bigger drill.
                For more information consult: https://www.eurocircuits.com/pcb-design-guidelines/drilled-holes/ """
            self.field_3D_model = '_3D_model'
            """ Name for the field controlling the 3D models used for a component """
            self.hide_excluded = False
            """ Default value for the `hide_excluded` option of various PCB outputs """
            self.kiauto_time_out_scale = 0.0
            """ Time-out multiplier for KiAuto operations """
            self.kiauto_wait_start = 0
            """ Time to wait for KiCad in KiAuto operations """
            self.impedance_controlled = False
            """ The PCB needs specific dielectric characteristics.
                KiCad 6: you should set this in the Board Setup -> Physical Stackup """
            self.output = GS.def_global_output
            """ Default pattern for output file names """
            self.pcb_finish = 'HAL'
            """ Finishing used to protect pads. Currently used for documentation and to choose default colors.
                KiCad 6: you should set this in the Board Setup -> Board Finish -> Copper Finish option.
                Currently known are None, HAL, HASL, HAL SnPb, HAL lead-free, ENIG, ENEPIG, Hard gold, ImAg, Immersion Silver,
                Immersion Ag, ImAu, Immersion Gold, Immersion Au, Immersion Tin, Immersion Nickel, OSP and HT_OSP """
            self.pcb_material = 'FR4'
            """ PCB core material. Currently used for documentation and to choose default colors.
                Currently known are FR1 to FR5 """
            self.remove_solder_paste_for_dnp = True
            """ When applying filters and variants remove the solder paste for components that won't be included """
            self.remove_adhesive_for_dnp = True
            """ When applying filters and variants remove the adhesive (glue) for components that won't be included """
            self.restore_project = False
            """ Restore the KiCad project after execution.
                Note that this option will undo operations like `set_text_variables` """
            self.set_text_variables_before_output = False
            """ Run the `set_text_variables` preflight before running each output that involves variants.
                This can be used when a text variable uses the variant and you want to create more than
                one variant in the same run. Note that this could be slow because it forces a board
                reload each time you run an output that uses variants """
            self.silk_screen_color = 'white'
            """ Color for the markings. Currently used for documentation and to choose default colors.
                KiCad 6: you should set this in the Board Setup -> Physical Stackup.
                Currently known are black and white """
            self.silk_screen_color_top = ''
            """ Color for the top silk screen. When not defined `silk_screen_color` is used.
                Read `silk_screen_color` help """
            self.silk_screen_color_bottom = ''
            """ Color for the bottom silk screen. When not defined `silk_screen_color` is used.
                Read `silk_screen_color` help """
            self.solder_mask_color = 'green'
            """ Color for the solder mask. Currently used for documentation and to choose default colors.
                KiCad 6: you should set this in the Board Setup -> Physical Stackup.
                Currently known are green, black, white, yellow, purple, blue and red """
            self.solder_mask_color_top = ''
            """ Color for the top solder mask. When not defined `solder_mask_color` is used.
                Read `solder_mask_color` help """
            self.solder_mask_color_bottom = ''
            """ Color for the bottom solder mask. When not defined `solder_mask_color` is used.
                Read `solder_mask_color` help """
            self.time_format = '%H-%M-%S'
            """ Format used for the time we started the script. Uses the `strftime` format """
            self.time_reformat = True
            """ Tries to reformat the PCB/SCH date using the `date_format`.
                This assumes you let KiCad fill this value and hence the time is in ISO format (YY-MM-DD) """
            self.units = ''
            """ [millimeters,inches,mils] Default units. Affects `position`, `bom` and `panelize` outputs.
                Also KiCad 6 dimensions """
            self.use_dir_for_preflights = True
            """ Use the global `dir` as subdir for the preflights """
            self.variant = ''
            """ Default variant to apply to all outputs """
            self.out_dir = ''
            """ Base output dir, same as command line `--out-dir` """
            self.environment = Environment
            """ [dict] Used to define environment variables used by KiCad.
                The values defined here are exported as environment variables and has
                more precedence than KiCad paths defined in the GUI.
                You can make reference to any OS environment variable using ${VARIABLE}.
                The KIPRJMOD is also available for expansion """
            self.field_lcsc_part = ''
            """ The name of the schematic field that contains the part number for the LCSC/JLCPCB distributor.
                When empty KiBot will try to discover it """
            self.allow_blind_buried_vias = True
            """ Allow the use of buried vias. This value is only used for KiCad 7+.
                For KiCad 5 and 6 use the design rules settings, stored in the project """
            self.allow_microvias = True
            """ Allow the use of micro vias. This value is only used for KiCad 7+.
                For KiCad 5 and 6 use the design rules settings, stored in the project """
            self.erc_grid = 50
            """ Grid size used for the ERC. This value must be in mils.
                This is needed for KiCad 7 in order to run the off grid check.
                Shouldn't be needed in KiCad 8.
                https://gitlab.com/kicad/code/kicad/-/issues/14110 """
            self.kicad_dnp_applied = True
            """ The KiCad v7 PCB flag *Do Not Populate* is applied to our fitted flag before running any filter """
            self.kicad_dnp_applies_to_3D = True
            """ The KiCad v7 PCB flag *Do Not Populate* is applied to our fitted flag for 3D models,
                even when no filter/variant is specified. Disabling `kicad_dnp_applied` also disables
                this flag """
            self.colored_tht_resistors = True
            """ Try to add color bands to the 3D models of KiCad THT resistors """
            self.field_tolerance = Optionable
            """ [string|list(string)] Name/s of the field/s used for the tolerance.
                Used while creating colored resistors and for the value split filter.
                The default is ['tolerance', 'tol'] """
            self.default_resistor_tolerance = 20
            """ When no tolerance is specified we use this value.
                Note that I know 5% is a common default, but technically speaking 20% is the default.
                Used while creating colored resistors """
            self.cache_3d_resistors = False
            """ Use a cache for the generated 3D models of colored resistors.
                Will save time, but you could need to remove the cache if you need to regenerate them """
            self.resources_dir = 'kibot_resources'
            """ Directory where various resources are stored. Currently we support colors and fonts.
                They must be stored in sub-dirs. I.e. kibot_resources/fonts/MyFont.ttf
                Note this is mainly useful for CI/CD, so you can store fonts and colors in your repo.
                Also note that the fonts are installed using a mechanism known to work on Debian,
                which is used by the KiBot docker images, on other OSs *your mileage may vary* """
            self.use_os_env_for_expand = True
            """ In addition to KiCad text variables also use the OS environment variables when expanding ${VARIABLE} """
            self.field_voltage = Optionable
            """ [string|list(string)] Name/s of the field/s used for the voltage raiting.
                Used for the value split filter.
                The default is ['voltage', 'v'] """
            self.field_package = Optionable
            """ [string|list(string)] Name/s of the field/s used for the package, not footprint.
                I.e. 0805, SOT-23, etc. Used for the value split filter.
                The default is ['package', 'pkg'] """
            self.field_temp_coef = Optionable
            """ [string|list(string)] Name/s of the field/s used for the temperature coefficient.
                I.e. X7R, NP0, etc. Used for the value split filter.
                The default is ['temp_coef', 'tmp_coef'] """
            self.field_power = Optionable
            """ [string|list(string)] Name/s of the field/s used for the power raiting.
                Used for the value split filter.
                The default is ['power', 'pow'] """
            self.invalidate_pcb_text_cache = 'auto'
            """ [auto,yes,no] Remove any cached text variable in the PCB. This is needed in order to force a text
                variables update when using `set_text_variables`. You might want to disable it when applying some
                changes to the PCB and create a new copy to send to somebody without changing the cached values.
                The `auto` value will remove the cached values only when using `set_text_variables` """
            self.git_diff_strategy = 'worktree'
            """ [worktree,stash] When computing a PCB/SCH diff it configures how do we preserve the current
                working state. The *worktree* mechanism creates a separated worktree, that then is just removed.
                The *stash* mechanism uses *git stash push/pop* to save the current changes. Using *worktree*
                is the preferred mechanism """
        self.set_doc('filters', " [list(dict)] KiBot warnings to be ignored ")
        self._filter_what = 'KiBot warnings'
        self.filters = FilterOptionsKiBot
        self._unknown_is_error = True
        self._error_context = 'global '

    def set_global(self, opt):
        # Command Line value has more priority
        cli_val = GS.cli_global_defs.get(opt, None)
        if cli_val is not None:
            logger.info('Using command line value `{}` for global option `{}`'.format(cli_val, opt))
            return cli_val
        # Now try to apply our default
        return getattr(self, opt)

    def get_data_from_layer(self, ly, materials, thicknesses):
        if ly.name == "F.SilkS":
            if ly.color:
                self.silk_screen_color_top = ly.color.lower()
                logger.debug("- F.SilkS color: "+ly.color)
        elif ly.name == "B.SilkS":
            if ly.color:
                self.silk_screen_color_bottom = ly.color.lower()
                logger.debug("- B.SilkS color: "+ly.color)
        elif ly.name == "F.Mask":
            if ly.color:
                self.solder_mask_color_top = ly.color.lower()
                logger.debug("- F.Mask color: "+ly.color)
        elif ly.name == "B.Mask":
            if ly.color:
                self.solder_mask_color_bottom = ly.color.lower()
                logger.debug("- B.Mask color: "+ly.color)
        elif ly.material:
            if not len(materials):
                materials.add(ly.material)
                self.pcb_material = ly.material
            elif ly.material not in materials:
                materials.add(ly.material)
                self.pcb_material += ' / '+ly.material
        elif ly.type == 'copper' and ly.thickness:
            if not len(thicknesses):
                thicknesses.add(ly.thickness)
                self.copper_thickness = str(int(ly.thickness))
            elif ly.thickness not in thicknesses:
                thicknesses.add(ly.thickness)
                self.copper_thickness += ' / '+str(int(ly.thickness))

    def get_stack_up(self):
        logger.debug("Looking for stack-up information in the PCB")
        pcb = None
        with open(GS.pcb_file, 'rt') as fh:
            try:
                pcb = load(fh)
            except SExpData as e:
                # Don't make it an error, will be detected and reported latter
                logger.debug("- Failed to load the PCB "+str(e))
        if pcb is None:
            return
        iter = sexp_iter(pcb, 'kicad_pcb/setup/stackup')
        if iter is None:
            return
        sp = next(iter, None)
        if sp is None:
            return
        logger.debug("- Found stack-up information")
        stackup = []
        materials = set()
        thicknesses = set()
        for e in sp[1:]:
            if isinstance(e, list) and isinstance(e[0], Symbol):
                name = e[0].value()
                value = None
                if len(e) > 1:
                    if isinstance(e[1], Symbol):
                        value = e[1].value()
                    else:
                        value = str(e[1])
                if name == 'copper_finish':
                    self.pcb_finish = value
                    logger.debug("- Copper finish: "+self.pcb_finish)
                elif name == 'edge_connector':
                    self.edge_connector = value
                    logger.debug("- Edge connector: "+self.edge_connector)
                elif name == 'castellated_pads':
                    self.castellated_pads = value == 'yes'
                    logger.debug("- Castellated pads: "+value)
                elif name == 'edge_plating':
                    self.edge_plating = value == 'yes'
                    logger.debug("- Edge plating: "+value)
                elif name == 'dielectric_constraints':
                    self.impedance_controlled = value == 'yes'
                    logger.debug("- Impedance controlled: "+value)
                elif name == 'layer':
                    lys = PCBLayer.parse(e)
                    for ly in lys:
                        stackup.append(ly)
                        self.get_data_from_layer(ly, materials, thicknesses)
        if stackup:
            GS.stackup = stackup
        if len(materials):
            logger.debug("- PCB Material/s: "+self.pcb_material)
        if len(thicknesses):
            logger.debug("- Copper thickness: "+self.copper_thickness)

    def config(self, parent):
        if GS.ki6 and GS.pcb_file and os.path.isfile(GS.pcb_file):
            self.get_stack_up()
        super().config(parent)
        self.field_tolerance = Optionable.force_list(self.field_tolerance, default=['tolerance', 'tol'])
        self.field_voltage = Optionable.force_list(self.field_voltage, default=['voltage', 'v'])
        self.field_package = Optionable.force_list(self.field_package, default=['package', 'pkg'])
        self.field_temp_coef = Optionable.force_list(self.field_temp_coef, default=['temp_coef', 'tmp_coef'])
        self.field_power = Optionable.force_list(self.field_power, default=['power', 'pow'])
        # Transfer options to the GS globals
        for option in filter(lambda x: x[0] != '_', self.__dict__.keys()):
            gl = 'global_'+option
            if hasattr(GS, gl):
                setattr(GS, gl, self.set_global(option))
        # Special cases
        if not GS.out_dir_in_cmd_line and self.out_dir:
            GS.out_dir = os.path.join(os.getcwd(), self.out_dir)
        if GS.global_kiauto_wait_start and int(GS.global_kiauto_wait_start) != GS.global_kiauto_wait_start:
            GS.global_kiauto_wait_start = int(GS.global_kiauto_wait_start)
            logger.warning(W_MUSTBEINT+'kiauto_wait_start must be integer, truncating to '+str(GS.global_kiauto_wait_start))
        # - Solder mask
        if GS.global_solder_mask_color_top and GS.global_solder_mask_color_bottom:
            # Top and bottom defined, use the top as general
            GS.global_solder_mask_color = GS.global_solder_mask_color_top
        else:
            if not GS.global_solder_mask_color_top:
                GS.global_solder_mask_color_top = GS.global_solder_mask_color
            if not GS.global_solder_mask_color_bottom:
                GS.global_solder_mask_color_bottom = GS.global_solder_mask_color
        # - Silk screen
        if GS.global_silk_screen_color_top and GS.global_silk_screen_color_bottom:
            GS.global_silk_screen_color = GS.global_silk_screen_color_top
        else:
            if not GS.global_silk_screen_color_top:
                GS.global_silk_screen_color_top = GS.global_silk_screen_color
            if not GS.global_silk_screen_color_bottom:
                GS.global_silk_screen_color_bottom = GS.global_silk_screen_color
        set_filters(self.unparsed)
        # 3D models aliases
        if isinstance(self.aliases_for_3d_models, list):
            KiConf.init(GS.pcb_file or GS.sch_file)
            logger.debug('Adding 3D models aliases from global config')
            for alias in self.aliases_for_3d_models:
                KiConf.aliases_3D[alias.name] = alias.value
                logger.debugl(1, '- {}={}'.format(alias.name, alias.value))
            logger.debugl(1, 'Finished adding aliases')


logger = get_logger(__name__)
GS.class_for_global_opts = Globals
