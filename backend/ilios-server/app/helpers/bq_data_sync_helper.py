"""Interfaces to insert data for BQ"""

import logging
import re
from abc import ABC, abstractmethod
from typing import Type

from pydantic import BaseModel

from app.bigquery.bigquery import BigQueryWriteEngine
from app.models.device import Device
from app.models.site import Site
from app.schema.bq_models import (
    BQDeviceCharacteristicsCreateSchema,
    BQDeviceCharacteristicsUpdateSchema,
    BQSiteCharacteristicsCreateSchema,
    BQSiteCharacteristicsUpdateSchema,
)
from app.settings import settings
from app.static.due_diligence_bq_keys import DD_BQ_QUANTITY_KEYS

logger = logging.getLogger(__name__)


class BQCharacteristicsHandler:
    """Manage BQ data inserts"""

    def __init__(
        self, table_name: str, conditions: dict, create_schema: Type[BaseModel], update_schema: Type[BaseModel]
    ):
        """
        Args:
            table_name (str): The name of the BQ table under the specific dataset
            conditions (dict): A dict with key-value pairs describing condition for the record filtering WHERE clause
            create_schema (Type[BaseModel]): Pydantic model which describes the full structure for new record insertion
            update_schema (Type[BaseModel]): Pydantic model which describes the subset of fields applied for update
        """
        self.bq_engine = BigQueryWriteEngine()
        self.table_id = self.gen_table_id(table_name)
        self.conditions = self.gen_conditions(conditions)
        self.create_schema = create_schema
        self.update_schema = update_schema

    def gen_table_id(self, table_name: str):
        """Generate table ID as combination of dataset name and table name itself"""
        return f"{self.bq_engine.bq_dataset_name}.{table_name}"

    @staticmethod
    def gen_conditions(conditions: dict):
        """Transform conditions key pairs into part of BQ statement"""
        return " AND ".join([f"{field_name}={field_value}" for field_name, field_value in conditions.items()])

    def get_record(self):
        return self.bq_engine.get_bq_record(self.table_id, self.conditions)

    def _insert_record(self, record: dict):
        return self.bq_engine.insert_bq_record(self.table_id, record)

    def _update_record(self, record: dict):
        return self.bq_engine.update_bq_record(self.table_id, record, self.conditions)

    def upsert_record(self, record: dict):
        """Create a new record or update existing one"""
        existing_record = self.get_record()
        if not existing_record:
            new_record_payload = self.create_schema(**record).model_dump(exclude_none=True)
            return self._insert_record(new_record_payload)
        update_record_payload = self.update_schema(**record).model_dump(exclude_none=True)
        return self._update_record(update_record_payload)


class CharacteristicsHandler(ABC):
    """Performs checks for the difference"""

    def __init__(
        self, table_name: str, conditions: dict, create_schema: Type[BaseModel], update_schema: Type[BaseModel]
    ):
        self.table_id = table_name
        self.conditions = conditions
        self.create_schema = create_schema
        self.update_schema = update_schema

    @staticmethod
    def _handle_null_value(dict_):
        """If input isn't dict: return empty dict"""
        if not isinstance(dict_, dict):
            return {}
        return dict_

    def _deep_diff(self, original_object: dict, updated_object_object: dict) -> dict:
        """
        Recursively find the difference between two dictionaries.
        Returns a dictionary with the differences where <updated_object_object> has different values.
        """
        # ensure both original and updated_object_object are valid dicts
        original_object = self._handle_null_value(original_object)
        updated_object_object = self._handle_null_value(updated_object_object)

        diff = {}
        for key in updated_object_object:
            if key not in original_object:
                # if key exists only in updated_object_object, add it to the diff
                diff[key] = updated_object_object[key]
            elif isinstance(updated_object_object[key], dict) and isinstance(original_object.get(key), dict):
                # TODO add tests
                # if both values are dictionaries, go deeper
                nested_diff = self._deep_diff(original_object[key], updated_object_object[key])
                # add to the diff recursion result
                if nested_diff:
                    diff[key] = nested_diff
            elif updated_object_object[key] != original_object.get(key):
                diff[key] = updated_object_object[key]
        return diff

    def sync_to_bq(self, old_record: dict, new_record: dict):
        """Checks if important fields (based on the schema) were changed.
        If True - make call to BQ to synchronize the values."""
        # find the differences between objects before/after update
        diff_fields = self._deep_diff(old_record, new_record)
        # since devices working with the nested fields, support it by method to define diff source object
        diff_fields = self._diff_postprocessing(diff_fields)
        # using update schema, check if fields required for the telemetry calculation were changed
        changed_fields = self.populate_update_schema(diff_fields)
        # no update needed, return
        if not changed_fields:
            return  # pragma: no cover

        # init BQ handler and upsert record using the create schema object
        bq_characteristics_handler = BQCharacteristicsHandler(
            self.table_id, self.conditions, self.create_schema, self.update_schema
        )
        upsert_record_payload = self.populate_create_schema(changed_fields)
        bq_characteristics_handler.upsert_record(upsert_record_payload)

    @abstractmethod
    def _diff_postprocessing(self, diff_object: dict):  # noqa: U100
        """Additional operations to transform diff result to the final look and feel"""

    @abstractmethod
    def populate_update_schema(self, diff_source: dict):  # noqa: U100
        """Based on the known schema, perform Platform to BQ mapping"""

    @abstractmethod
    def populate_create_schema(self, diff_source: dict):  # noqa: U100
        """Extend update schema with required fields"""


class DeviceCharacteristicsHandler(CharacteristicsHandler):
    def __init__(self, device: Device):
        super().__init__(
            table_name=settings.bq_device_characteristics_table,
            conditions={"site_id": device.site_id, "device_id": device.id},
            create_schema=BQDeviceCharacteristicsCreateSchema,
            update_schema=BQDeviceCharacteristicsUpdateSchema,
        )
        self.device = device

    def _diff_postprocessing(self, diff_object: dict):
        """Check if power section was updated"""
        return diff_object.get("power", {})

    def populate_update_schema(self, diff_object: dict):
        return self.update_schema(
            cec_efficiency=diff_object.get("cec_efficiency"),
            number_of_pv_modules_per_inverter=diff_object.get("pv_modules_number"),
            thermal_coefficient_of_power=diff_object.get("power_thermal_coefficient"),
            power_tolerance_min=diff_object.get("min_power_tolerance"),
            power_tolerance_max=diff_object.get("max_power_tolerance"),
            year_1_degradation=diff_object.get("year_1_degradation"),
            annual_degradation=diff_object.get("annual_degradation"),
        ).model_dump(exclude_none=True)

    def populate_create_schema(self, update_schema_payload: dict):
        return self.create_schema(
            site_id=self.device.site_id,
            device_id=self.device.id,
            device_category=self.device.category.name,
            **update_schema_payload,
        ).model_dump()


class SiteCharacteristicsHandler(CharacteristicsHandler):
    def __init__(self, site: Site):
        super().__init__(
            table_name=settings.bq_site_characteristics_table,
            conditions={"site_id": site.id},
            create_schema=BQSiteCharacteristicsCreateSchema,
            update_schema=BQSiteCharacteristicsUpdateSchema,
        )
        self.site = site

    def _diff_postprocessing(self, diff_object: dict):
        """No postprocessing required, return as is"""
        return diff_object

    def populate_update_schema(self, diff_object: dict):
        return self.update_schema(
            permission_to_operate=diff_object.get("permission_to_operate"),
            dc_ohmic_wiring_loss=diff_object.get("dc_wiring_loss"),
            ac_ohmic_wiring_loss=diff_object.get("ac_wiring_loss"),
            medium_voltage_transfo_loss=diff_object.get("medium_voltage_loss"),
            mv_line_ohmic_loss=diff_object.get("mv_line_loss"),
            module_wattage=diff_object.get("module_wattage"),
            module_quantity=diff_object.get("module_quantity"),
            inverter_wattage=diff_object.get("inverter_wattage"),
            inverter_quantity=diff_object.get("inverter_quantity"),
            estimated_generation=diff_object.get("estimated_generation"),
        ).model_dump(exclude_none=True)

    def populate_create_schema(self, update_schema_payload: dict):
        return self.create_schema(site_id=self.site.id, **update_schema_payload).model_dump()


class SiteDDCharacteristicsHandler(SiteCharacteristicsHandler):
    def _diff_postprocessing(self, diff_object: dict):
        """Overwrite parent class method.
        For the Due Diligence keys, we need clean up the input value and group year1 metrics into the array
        """
        result = {}
        for key, value in diff_object.items():
            normalized_value = self.parse_numbers(value) if key in DD_BQ_QUANTITY_KEYS else value
            result[key] = normalized_value
        return result

    @staticmethod
    def parse_numbers(input_value):
        """Get float value from the string"""
        match = re.match(r"(\d*\.?\d+)", input_value.lower())
        if match:
            return float(match.group(1))
