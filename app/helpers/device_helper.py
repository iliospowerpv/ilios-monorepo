import math
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status

from app.crud.alert import AlertCRUD
from app.helpers.telemetry.bigquery import TelemetryDeviceBigQuery
from app.models.device import Device, DeviceCategories, DeviceManufacturers, DeviceStatuses, DeviceTypes
from app.settings import settings

# TODO maintain static
TELEMETRY_DEVICES_CATEGORIES = [DeviceCategories.inverter, DeviceCategories.meter, DeviceCategories.weather_station]

category_types_mapper = {
    DeviceCategories.inverter: [DeviceTypes.string, DeviceTypes.micro_inverter, DeviceTypes.power_optimizers],
    DeviceCategories.rack_mount: [
        DeviceTypes.canopy,
        DeviceTypes.carport,
        DeviceTypes.dual_axis,
        DeviceTypes.fixed_tilt,
        DeviceTypes.single_axis,
    ],
    DeviceCategories.battery: [DeviceTypes.agm, DeviceTypes.flow, DeviceTypes.lithium_ion, DeviceTypes.nickel_cadmium],
    DeviceCategories.camera: [
        DeviceTypes.bullet,
        DeviceTypes.cctv,
        DeviceTypes.dome,
        DeviceTypes.ptz,
        DeviceTypes.thermal,
    ],
    DeviceCategories.module: [DeviceTypes.bifacial, DeviceTypes.monofacial],
    DeviceCategories.network_connection: [
        DeviceTypes.cellular_internet,
        DeviceTypes.fiber_internet,
        DeviceTypes.satellite_internet,
        DeviceTypes.terrestrial_internet,
        DeviceTypes.point_to_point,
        DeviceTypes.vpn,
    ],
    DeviceCategories.transformer: [
        DeviceTypes.ground,
        DeviceTypes.inverter_transformer,
        DeviceTypes.collector,
        DeviceTypes.auxiliary,
        DeviceTypes.earthing,
        DeviceTypes.voltage_regulator,
    ],
    DeviceCategories.combiner_box: [DeviceTypes.other],
    DeviceCategories.mbod_gateway: [DeviceTypes.other],
    DeviceCategories.meter: [DeviceTypes.other],
    DeviceCategories.modem: [DeviceTypes.other],
    DeviceCategories.network_gateway: [DeviceTypes.other],
    DeviceCategories.weather_station: [DeviceTypes.other],
}
category_manufacturers_mapper = {
    DeviceCategories.inverter: [
        DeviceManufacturers.chint_power_systems,
        DeviceManufacturers.sma,
        DeviceManufacturers.sungrow,
        DeviceManufacturers.advanced_energy,
        DeviceManufacturers.alencon_systems,
        DeviceManufacturers.abb_ltd,
        DeviceManufacturers.chilicon_power,
        DeviceManufacturers.cybo_energy,
        DeviceManufacturers.enphase_energy,
        DeviceManufacturers.fimer,
        DeviceManufacturers.fronius_international,
        DeviceManufacturers.ginlong_technologies_co,
        DeviceManufacturers.goodwe,
        DeviceManufacturers.growatt,
        DeviceManufacturers.huawei,
        DeviceManufacturers.kaco_new_energy_gmbh,
        DeviceManufacturers.midnite_solar,
        DeviceManufacturers.nep,
        DeviceManufacturers.outback_power,
        DeviceManufacturers.power_electronics,
        DeviceManufacturers.schneider_electric,
        DeviceManufacturers.solaredge,
        DeviceManufacturers.tmeic,
    ],
    DeviceCategories.rack_mount: [
        DeviceManufacturers.crossrail,
        DeviceManufacturers.panel_claw,
        DeviceManufacturers.terrasmart,
        DeviceManufacturers.voyager,
        DeviceManufacturers.fiveb_solar,
        DeviceManufacturers.allearth_renewables,
        DeviceManufacturers.apa_solar_racking,
        DeviceManufacturers.array_technologies,
        DeviceManufacturers.bci_engineering,
        DeviceManufacturers.clenergy,
        DeviceManufacturers.ecofasten,
        DeviceManufacturers.empery_solar,
        DeviceManufacturers.ftc_solar,
        DeviceManufacturers.ironridge,
        DeviceManufacturers.kb_racking_inc,
        DeviceManufacturers.magerack,
        DeviceManufacturers.m_bar,
        DeviceManufacturers.nuance_energy,
        DeviceManufacturers.omco_solar,
        DeviceManufacturers.prosolar,
        DeviceManufacturers.quick_mount_pv,
        DeviceManufacturers.rbi,
        DeviceManufacturers.renusol,
        DeviceManufacturers.roof_tech,
        DeviceManufacturers.snapnrack,
        DeviceManufacturers.sky_grip,
        DeviceManufacturers.solarpod,
        DeviceManufacturers.sollega_inc,
        DeviceManufacturers.sun_action,
        DeviceManufacturers.sun_modo_corp,
        DeviceManufacturers.suntelite,
        DeviceManufacturers.unirac,
    ],
    DeviceCategories.battery: [
        DeviceManufacturers.nine_sun_solar,
        DeviceManufacturers.abb_ltd,
        DeviceManufacturers.absen_energy,
        DeviceManufacturers.bloom_energy,
        DeviceManufacturers.byd,
        DeviceManufacturers.electriq_power,
        DeviceManufacturers.ess_tech_in,
        DeviceManufacturers.fluence,
        DeviceManufacturers.lg_chem,
        DeviceManufacturers.neovolta,
        DeviceManufacturers.nexera_energy,
        DeviceManufacturers.panasonic,
        DeviceManufacturers.saft_batteries,
        DeviceManufacturers.samsung_sdi,
        DeviceManufacturers.siemens,
        DeviceManufacturers.sonnen,
        DeviceManufacturers.tesla,
        DeviceManufacturers.toshiba,
    ],
    DeviceCategories.module: [
        DeviceManufacturers.aditi_solar,
        DeviceManufacturers.ae_solar,
        DeviceManufacturers.ascent_solar,
        DeviceManufacturers.auxin_solar_inc,
        DeviceManufacturers.axitech,
        DeviceManufacturers.bluesun,
        DeviceManufacturers.byd,
        DeviceManufacturers.canadian_solar,
        DeviceManufacturers.certainteed_solar,
        DeviceManufacturers.c_sun,
        DeviceManufacturers.first_solar,
        DeviceManufacturers.hanwha_q_cells,
        DeviceManufacturers.hareon,
        DeviceManufacturers.heliene,
        DeviceManufacturers.ht_saae,
        DeviceManufacturers.ja_solar_holdings,
        DeviceManufacturers.jinkosolar,
        DeviceManufacturers.kyocera,
        DeviceManufacturers.lg_electronics,
        DeviceManufacturers.longi_solar,
        DeviceManufacturers.mission_solar,
        DeviceManufacturers.panasonic,
        DeviceManufacturers.rec,
        DeviceManufacturers.slifab_solar,
        DeviceManufacturers.solar4america,
        DeviceManufacturers.sunpower,
        DeviceManufacturers.suntech_power,
        DeviceManufacturers.trina_solar,
        DeviceManufacturers.yingli_solar,
    ],
    DeviceCategories.network_connection: [
        DeviceManufacturers.at_n_t,
        DeviceManufacturers.cricket,
        DeviceManufacturers.charter_communications,
        DeviceManufacturers.spacex,
        DeviceManufacturers.sprint,
        DeviceManufacturers.t_mobile,
        DeviceManufacturers.verizon,
        DeviceManufacturers.xfinity,
        DeviceManufacturers.other,
    ],
    DeviceCategories.camera: [DeviceManufacturers.other],
    DeviceCategories.combiner_box: [DeviceManufacturers.other],
    DeviceCategories.mbod_gateway: [DeviceManufacturers.other],
    DeviceCategories.meter: [DeviceManufacturers.other],
    DeviceCategories.modem: [DeviceManufacturers.other],
    DeviceCategories.network_gateway: [DeviceManufacturers.other],
    DeviceCategories.transformer: [DeviceManufacturers.other],
    DeviceCategories.weather_station: [DeviceManufacturers.other],
}

categories_without_types = [
    DeviceCategories.combiner_box,
    DeviceCategories.mbod_gateway,
    DeviceCategories.meter,
    DeviceCategories.modem,
    DeviceCategories.network_gateway,
    DeviceCategories.weather_station,
]
categories_without_manufacturers = [
    DeviceCategories.camera,
    DeviceCategories.combiner_box,
    DeviceCategories.mbod_gateway,
    DeviceCategories.meter,
    DeviceCategories.modem,
    DeviceCategories.network_gateway,
    DeviceCategories.transformer,
    DeviceCategories.weather_station,
]

# Extends type and category mappers with ability to pass Other value for categories/types


def validate_device_type_manufacturer(category, device_type, manufacturer):

    def raise_exception(message):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message)

    if manufacturer:
        category_manufacturers_options = category_manufacturers_mapper.get(category)
        if not category_manufacturers_options:  # pragma: no cover
            raise_exception(f"Server error. There is misconfiguration for the {category.value} manufacturers list.")
        if manufacturer not in category_manufacturers_options:
            available_options = ", ".join([f"'{cat.value}'" for cat in category_manufacturers_options])
            raise_exception(
                f"There is no '{manufacturer.value}' manufacturer in '{category.value}' category. "
                f"Input should be: {available_options}"
            )

    if device_type:
        category_types_options = category_types_mapper.get(category)
        if not category_types_options:  # pragma: no cover
            raise_exception(f"Server error. There is misconfiguration for the {category.value} types list.")
        if device_type not in category_types_options:
            available_options = ", ".join([f"'{cat.value}'" for cat in category_types_options])
            raise_exception(
                f"There is no '{device_type.value}' type in '{category.value}' category. "
                f"Input should be: {available_options}"
            )


def get_site_devices_info(site, db_session):
    """Retrieve statistics for site devices which includes category name, devices count and critical alerts count
    per each device category available on the platform"""
    devices_critical_alerts = AlertCRUD(db_session).get_critical_devices_alerts_stats(
        [device.id for device in site.devices]
    )
    devices_info = []
    devices_bq_data = get_devices_last_reported(site.devices)
    for device_category in DeviceCategories:
        # nullify critical alerts number to ensure we start count from 0 for each device type
        critical_errors = 0
        device_critical_alert = [
            device_critical_alert_record
            for device_critical_alert_record in devices_critical_alerts
            if device_critical_alert_record.category == device_category
        ]
        if device_critical_alert:
            critical_errors = device_critical_alert[0].total
        devices_in_category = [device.id for device in site.devices if device.category == device_category]
        devices_info.append(
            {
                "device_type": device_category,
                "critical_errors": critical_errors,
                "devices": len(devices_in_category),
                "no_respond": get_devices_no_respond_count(device_category, devices_in_category, devices_bq_data),
            }
        )

    return devices_info


def set_device_default_fields(device_payload):
    """Set device default fields:

    status: 'Available Inventory'
    performance: random device performance from 0 to 250 percents
    type: Other for categories without types
    manufacturer: 'Other' for categories without manufacturers
    """

    device_payload["status"] = DeviceStatuses.available_inventory
    if device_payload["category"] in categories_without_manufacturers:
        device_payload["manufacturer"] = DeviceManufacturers.other
    if device_payload["category"] in categories_without_types:
        device_payload["type"] = DeviceTypes.other


def get_devices_last_reported(devices: Optional[List[Device]]):
    """Retrieve telemetry data about device last reported time"""
    # get IDs of mapped devices which supports telemetry
    mapped_telemetry_devices_ids = [
        device.id
        for device in devices
        if device.category in TELEMETRY_DEVICES_CATEGORIES and device.telemetry_mapping is not None
    ]
    # don't make BQ call if no meaningful devices were mapped
    telemetry_devices_data = (
        TelemetryDeviceBigQuery().get_device_last_reported(mapped_telemetry_devices_ids)
        if mapped_telemetry_devices_ids
        else []
    )
    return telemetry_devices_data


def get_devices_no_respond_count(device_category, devices_in_category, telemetry_devices_details):
    """Calculate number of no responded devices based on the category and telemetry details"""
    # devices not supported by the telemetry doesn't value for the 'no respond' number
    if device_category not in TELEMETRY_DEVICES_CATEGORIES:
        return 0
    no_respond_devices_count = 0
    # find telemetry details for devices in chosen category
    category_devices_telemetry = [item for item in telemetry_devices_details if item["device_id"] in devices_in_category]
    for telemetry_item in category_devices_telemetry:
        # calculate difference between now and device last report to treat it as 'no respond'
        response_diff = datetime.now(timezone.utc).replace(tzinfo=None) - telemetry_item["device_last_report_ts"]
        if response_diff.seconds >= settings.device_no_respond_threshold:
            no_respond_devices_count += 1
    return no_respond_devices_count


def get_availability_metrics(device: Device):
    """Get telemetry values for MTBF (mean time between failures) and MTTR (mean time to recovery)"""
    response = {"mtbf": None, "mttr": None}
    if device.category not in TELEMETRY_DEVICES_CATEGORIES:
        return {"mtbf": "N/A", "mttr": "N/A"}
    if not device.telemetry_mapping:
        return response
    telemetry_devices_data = TelemetryDeviceBigQuery().get_device_availability_metrics(
        [device.id], get_availability_metrics_start_time(device)
    )
    if telemetry_devices_data:
        response["mtbf"] = transform_availability_metric(telemetry_devices_data[0]["mtbf"])
        response["mttr"] = transform_availability_metric(telemetry_devices_data[0]["mttr"])
    return response


def transform_availability_metric(value):
    """Transform from hours to days and round up"""
    return math.ceil(value / 24)


def get_availability_metrics_start_time(device: Device):
    """Define interval start as Permission to Operate field (primary) or device das connection creation (secondary)"""
    if device.site.additional_fields:
        if device.site.additional_fields.permission_to_operate:
            return datetime.combine(device.site.additional_fields.permission_to_operate, datetime.min.time())
    return device.telemetry_mapping.created_at
