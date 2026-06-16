import {
  DEVICE_CATEGORY_GROUPS,
  categoriesForGroupKey,
  deriveEligibilityChip,
  deriveTelemetryStatusChip,
  roleLabel,
  buildDevicesCsv,
  escapeCsvField,
  DEVICE_CSV_COLUMNS,
  UNAVAILABLE_CHIP,
  type DeviceCsvRow
} from '../deviceDiagnostics';
import type { DeviceEligibilityDiagnostic } from '../../../types/telemetryV2';

const makeDiag = (overrides: Partial<DeviceEligibilityDiagnostic> = {}): DeviceEligibilityDiagnostic => ({
  device_id: 1,
  name: 'Inverter A',
  category: 'Inverter',
  device_role: null,
  mappable: true,
  can_drive_expected: false,
  telemetry_capable: true,
  weather_source_capable: false,
  production_meter_capable: false,
  gateway_capable: false,
  virtual_device: false,
  mapped_status: 'unmapped_eligible',
  is_mapped: false,
  source_provider: null,
  external_device_type: null,
  eligibility_reason: null,
  ineligibility_reason: null,
  weather_semantics: null,
  indicators: [],
  ...overrides
});

describe('category filter grouping (button -> categories)', () => {
  it('maps each group key to the expected DeviceCategories VALUES', () => {
    expect(categoriesForGroupKey('all')).toEqual([]);
    expect(categoriesForGroupKey('inverters')).toEqual(['Inverter']);
    expect(categoriesForGroupKey('production_meters')).toEqual(['Meter']);
    expect(categoriesForGroupKey('weather')).toEqual(['Weather Station']);
    expect(categoriesForGroupKey('gateways_das')).toEqual(['MBOD Gateway', 'Network Gateway']);
    expect(categoriesForGroupKey('data_captures')).toEqual(['Modem', 'Network Connection', 'Combiner Box']);
  });

  it('returns an empty (no-filter) list for an unknown key', () => {
    expect(categoriesForGroupKey('does-not-exist')).toEqual([]);
  });

  it('exposes "All" first with an empty category list', () => {
    expect(DEVICE_CATEGORY_GROUPS[0]).toMatchObject({ key: 'all', categories: [] });
  });
});

describe('deriveEligibilityChip (chip-state derivation)', () => {
  it('returns an honest Unavailable chip when diagnostics are missing', () => {
    expect(deriveEligibilityChip(undefined)).toEqual(UNAVAILABLE_CHIP);
    expect(deriveEligibilityChip(undefined).label).toBe('Unavailable');
  });

  it('labels an expected-driver device and colors it primary', () => {
    const chip = deriveEligibilityChip(makeDiag({ can_drive_expected: true }));
    expect(chip.label).toBe('Expected driver');
    expect(chip.color).toBe('primary');
  });

  it('labels a weather source and colors it info when mappable', () => {
    const chip = deriveEligibilityChip(makeDiag({ weather_source_capable: true }));
    expect(chip.label).toBe('Weather source');
    expect(chip.color).toBe('info');
  });

  it('labels a non-mappable device Not eligible with default color', () => {
    const chip = deriveEligibilityChip(makeDiag({ mappable: false }));
    expect(chip.label).toBe('Not eligible');
    expect(chip.color).toBe('default');
  });
});

describe('roleLabel precedence', () => {
  it('prefers expected-driver over every other capability', () => {
    const diag = makeDiag({
      can_drive_expected: true,
      weather_source_capable: true,
      production_meter_capable: true,
      gateway_capable: true
    });
    expect(roleLabel(diag)).toBe('Expected driver');
  });

  it('falls back to Meter (inspection-only) for a production meter', () => {
    expect(roleLabel(makeDiag({ production_meter_capable: true }))).toBe('Meter (inspection-only)');
  });
});

describe('deriveTelemetryStatusChip (V2 liveness)', () => {
  it('returns Unavailable for missing diagnostics (never fabricates Mapped)', () => {
    expect(deriveTelemetryStatusChip(undefined)).toEqual(UNAVAILABLE_CHIP);
  });

  it('maps mapped_status to the right liveness chip', () => {
    expect(deriveTelemetryStatusChip(makeDiag({ mapped_status: 'mapped' }))).toMatchObject({
      label: 'Mapped',
      color: 'success'
    });
    expect(deriveTelemetryStatusChip(makeDiag({ mapped_status: 'unmapped_eligible' }))).toMatchObject({
      label: 'Missing telemetry',
      color: 'warning'
    });
    expect(deriveTelemetryStatusChip(makeDiag({ mapped_status: 'ineligible' }))).toMatchObject({
      label: 'Not mappable',
      color: 'default'
    });
  });

  it('returns Unavailable for an unrecognized mapped_status', () => {
    expect(deriveTelemetryStatusChip(makeDiag({ mapped_status: 'something_new' }))).toEqual(UNAVAILABLE_CHIP);
  });
});

describe('escapeCsvField', () => {
  it('quotes fields containing commas, quotes, or newlines and doubles quotes', () => {
    expect(escapeCsvField('plain')).toBe('plain');
    expect(escapeCsvField('a,b')).toBe('"a,b"');
    expect(escapeCsvField('say "hi"')).toBe('"say ""hi"""');
    expect(escapeCsvField('line1\nline2')).toBe('"line1\nline2"');
  });
});

describe('buildDevicesCsv', () => {
  const devices: DeviceCsvRow[] = [
    {
      id: 1,
      asset_id: 'AID-1',
      name: 'Inverter, A',
      category: 'Inverter',
      status: 'Active',
      das_connection_status: 'Connected',
      manufacturer: 'Acme',
      capacity: 100,
      type: 'string',
      model: 'X1',
      serial_number: 'SN1'
    },
    {
      id: 2,
      asset_id: 'AID-2',
      name: 'Meter B',
      category: 'Meter',
      status: 'Active',
      das_connection_status: 'Not Connected',
      manufacturer: 'Beta',
      capacity: null,
      type: 'revenue',
      model: 'M2',
      serial_number: 'SN2'
    }
  ];

  it('emits a header row matching the configured columns', () => {
    const csv = buildDevicesCsv(devices, new Map());
    const headerLine = csv.split('\n')[0];
    expect(headerLine).toBe(DEVICE_CSV_COLUMNS.map(c => c.header).join(','));
    expect(headerLine).toContain('Eligibility');
    expect(headerLine).toContain('Telemetry Status');
  });

  it('merges diagnostics per device and quotes embedded commas', () => {
    const diagMap = new Map<number, DeviceEligibilityDiagnostic>([
      [1, makeDiag({ device_id: 1, can_drive_expected: true, mapped_status: 'mapped' })]
    ]);
    const lines = buildDevicesCsv(devices, diagMap).split('\n');
    // Row for device 1: name has a comma so it must be quoted; diagnostics resolved.
    expect(lines[1]).toContain('"Inverter, A"');
    expect(lines[1]).toContain('Expected driver');
    expect(lines[1]).toContain('Mapped');
  });

  it('exports an honest Unavailable for devices absent from diagnostics', () => {
    const lines = buildDevicesCsv(devices, new Map()).split('\n');
    // Device 2 has no diagnostics entry -> both diagnostics columns are Unavailable.
    const row2 = lines[2];
    const cells = row2.split(',');
    expect(cells[cells.length - 1]).toBe('Unavailable'); // Telemetry Status
    expect(cells[cells.length - 2]).toBe('Unavailable'); // Eligibility
  });

  it('renders an empty capacity cell rather than fabricating a 0', () => {
    const lines = buildDevicesCsv(devices, new Map()).split('\n');
    // Device 2 capacity is null -> empty cell, not "0".
    const capacityIndex = DEVICE_CSV_COLUMNS.findIndex(c => c.header === 'Capacity');
    expect(lines[2].split(',')[capacityIndex]).toBe('');
  });
});
