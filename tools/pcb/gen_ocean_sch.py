



















from skidl import Part, Net, generate_schematic, generate_netlist, set_default_tool

set_default_tool("kicad10")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "hardware", "release",
                                    "electrical", "ecocell-ocean"))

NETS = """
GND +3V3 +5V VBAT VIN EN NTC PROG CHRG_ST STDBY_ST LED_STDBY_A LED_CHRG_A
SW FB EN_BOOST
VBIAS HYDRO_SIG AFE_INP AFE_N AFE_OUT ADC_AIN ADC_RST REFIO REFCAP
CTD_S_P CTD_S_N CTD_EXC_P CTD_EXC_N LDR_OUT
SPI2_SCK SPI2_MOSI SPI2_MISO SPI2_CS SD_CS
