export const DeviceCategory = Object.freeze({
  Battery: 'Battery',
  Camera: 'Camera',
  CombinerBox: 'Combiner Box',
  Inverter: 'Inverter',
  MBODGateway: 'MBOD Gateway',
  Meter: 'Meter',
  Modem: 'Modem',
  Module: 'Module',
  NetworkConnection: 'Network Connection',
  NetworkGateway: 'Network Gateway',
  RackMount: 'Rack Mount',
  Transformer: 'Transformer',
  WeatherStation: 'Weather Station'
});

export type DeviceCategoryValue = (typeof DeviceCategory)[keyof typeof DeviceCategory];

const batteryTypes = Object.freeze(['AGM', 'Flow', 'Lithium Ion', 'Nickel Cadmium']);
const cameraTypes = Object.freeze(['Bullet', 'CCTV', 'Dome', 'PTZ', 'Thermal']);
const moduleTypes = Object.freeze(['Bifacial', 'Monofacial']);
const networkConnectionTypes = Object.freeze([
  'Internet via Cellular',
  'Internet via Fiber',
  'Internet via Satellite',
  'Internet via Terrestrial',
  'Point to Point',
  'VPN'
]);
const transformerTypes = Object.freeze([
  'Ground',
  'Inverter Transformer',
  'Collector',
  'Auxiliary',
  'Earthing',
  'Voltage Regulator'
]);
const inverterTypes = Object.freeze(['String', 'Micro Inverter', 'Power Optimizers']);
const rackMountTypes = Object.freeze(['Canopy', 'Carport', 'Dual Axis', 'Fixed Tilt', 'Single Axis']);

export const DeviceTypesMap: Readonly<{ [key in DeviceCategoryValue]: readonly string[] | null }> = Object.freeze({
  [DeviceCategory.Battery]: batteryTypes,
  [DeviceCategory.Camera]: cameraTypes,
  [DeviceCategory.CombinerBox]: null,
  [DeviceCategory.MBODGateway]: null,
  [DeviceCategory.Meter]: null,
  [DeviceCategory.Modem]: null,
  [DeviceCategory.Module]: moduleTypes,
  [DeviceCategory.RackMount]: rackMountTypes,
  [DeviceCategory.NetworkConnection]: networkConnectionTypes,
  [DeviceCategory.NetworkGateway]: null,
  [DeviceCategory.Transformer]: transformerTypes,
  [DeviceCategory.WeatherStation]: null,
  [DeviceCategory.Inverter]: inverterTypes
});

const batteryManufacturers = Object.freeze([
  '9Sun Solar',
  'ABB Ltd',
  'Absen Energy',
  'Bloom Energy',
  'BYD',
  'Electriq Power',
  'ESS Tech In',
  'Fluence',
  'LG Chem',
  'NeoVolta',
  'NexEra Energy',
  'Panasonic',
  'Saft Batteries',
  'Samsung SDI',
  'Siemens',
  'Sonnen',
  'Tesla',
  'Toshiba'
]);

const inverterManufacturers = Object.freeze([
  'Advanced Energy',
  'Alencon Systems',
  'ABB Ltd',
  'Chilicon Power',
  'Cybo Energy',
  'Enphase Energy',
  'FIMER',
  'Fronius International',
  'Ginlong Technologies Co',
  'Goodwe',
  'Growatt',
  'Huawei',
  'KACO New Energy GmbH',
  'MidNite Solar',
  'NEP',
  'OutBack Power',
  'Power Electronics',
  'Schneider Electric',
  'SolarEdge',
  'TMEIC',
  'Chint Power Systems',
  'SMA',
  'Sungrow'
]);

const moduleManufacturers = Object.freeze([
  'Aditi Solar',
  'AE Solar',
  'Ascent Solar',
  'Auxin Solar Inc.',
  'Axitech',
  'Bluesun',
  'BYD',
  'Canadian Solar',
  'CertainTeed Solar',
  'C Sun',
  'First Solar',
  'Hanwha Q Cells',
  'Hareon',
  'Heliene',
  'HT-SAAE',
  'JA Solar Holdings',
  'JinkoSolar',
  'Kyocera',
  'LG Electronics',
  'LONGi Solar',
  'Mission Solar',
  'Panasonic',
  'REC',
  'Slifab Solar',
  'Solar4America',
  'SunPower',
  'Suntech Power',
  'Trina Solar',
  'Yingli Solar'
]);

const networkConnectionManufacturers = Object.freeze([
  'AT&T',
  'Cricket',
  'Charter Communications (Spectrum)',
  'SpaceX',
  'Sprint',
  'T-Mobile',
  'Verizon',
  'Xfinity',
  'Other'
]);

const rackMountManufacturers = Object.freeze([
  '5B Solar',
  'AllEarth Renewables',
  'APA Solar Racking',
  'Array Technologies',
  'BCI Engineering',
  'Clenergy',
  'Crossrail',
  'EcoFasten',
  'Empery Solar',
  'FTC Solar',
  'IronRidge',
  'KB Racking Inc.',
  'Magerack',
  'M Bar',
  'Nuance Energy',
  'OMCO Solar',
  'Panel Claw',
  'ProSolar',
  'Quick Mount PV',
  'RBI',
  'Renusol',
  'Roof Tech',
  'SnapNrack',
  'Sky Grip',
  'SolarPod',
  'Sollega Inc',
  'Sun Action',
  'Sun Modo Corp',
  'Suntelite',
  'Terrasmart',
  'Unirac',
  'Voyager'
]);

export const DeviceManufacturersMap: Readonly<{ [key in DeviceCategoryValue]: readonly string[] | null }> =
  Object.freeze({
    [DeviceCategory.Battery]: batteryManufacturers,
    [DeviceCategory.Camera]: null,
    [DeviceCategory.CombinerBox]: null,
    [DeviceCategory.MBODGateway]: null,
    [DeviceCategory.Meter]: null,
    [DeviceCategory.Modem]: null,
    [DeviceCategory.Module]: moduleManufacturers,
    [DeviceCategory.RackMount]: rackMountManufacturers,
    [DeviceCategory.NetworkConnection]: networkConnectionManufacturers,
    [DeviceCategory.NetworkGateway]: null,
    [DeviceCategory.Transformer]: null,
    [DeviceCategory.WeatherStation]: null,
    [DeviceCategory.Inverter]: inverterManufacturers
  });
