class FSDevice:
    def __init__(self, _id: int, external_id: str):
        self.id = _id
        self.external_id = external_id

    @staticmethod
    def from_dict(source: dict) -> "FSDevice":
        # Dict structure: {"id": 1}
        return FSDevice(source["id"], source["external_id"])

    def to_dict(self):
        return {"id": self.id, "external_id": self.external_id}


class FSSite:
    def __init__(self, _id: int, external_id: str, connection_id: int, devices=None):
        if devices is None:
            devices = []
        self.id = _id
        self.external_id = external_id
        self.connection_id = connection_id
        self.devices = devices

    @staticmethod
    def from_dict(source):
        # Dict structure: {"id": 3, "external_id": "qwd12", "connection_id": 2, "devices": [{"id": 4}, {"id": 5}]}
        devices = [FSDevice.from_dict(device_dict) for device_dict in source["devices"]]
        return FSSite(source["id"], source["external_id"], source["connection_id"], devices)

    def to_dict(self):
        devices = [device.to_dict() for device in self.devices]
        return {
            "id": self.id,
            "external_id": self.external_id,
            "connection_id": self.connection_id,
            "devices": devices,
        }


class FSConnection:
    def __init__(self, _id, data_provider, token_secret_id):
        self.id = _id
        self.data_provider = data_provider
        self.token_secret_id = token_secret_id

    @staticmethod
    def from_dict(source):
        return FSConnection(source["id"], source["data_provider"], source["token_secret_id"])

    def to_dict(self):
        return {
            "id": self.id,
            "data_provider": self.data_provider,
            "token_secret_id": self.token_secret_id,
        }


class FSCompanyConfig:
    """Object representation of Firestore Company configuration"""

    def __init__(self, _id: int, connections: list, sites=None):
        if sites is None:
            sites = []
        self.id = _id
        self.sites = sites
        self.connections = connections

    @staticmethod
    def from_dict(source):
        """
        Dict structure {"id": 1,
                        "connections": [{
                                        "id": 2,
                                        "data_provider": "kmc",
                                        "token_secret_id": "projects/62796939168/secrets/test/versions/latest"
                                        }
                                        ],
                        "sites": [{"id": 3, "external_id": "sada" "connection_id": 2,
                                  "devices": [{"id": 4, "external_id": "21sa"}, {"id": 5, "external_id": "sadf21"}]}],
                        }
        """
        connections = [FSConnection.from_dict(connection_dict) for connection_dict in source["connections"]]
        sites = [FSSite.from_dict(site_dict) for site_dict in source["sites"]]
        return FSCompanyConfig(source["id"], connections, sites)

    def to_dict(self):
        sites = [site.to_dict() for site in self.sites]
        connections = [connection.to_dict() for connection in self.connections]
        return {"id": self.id, "sites": sites, "connections": connections}

    def delete_connection(self, connection_id):
        # Update connections/sites list and exclude connection for delete for further update in Firestore
        self.connections = [connection for connection in self.connections if not (connection.id == connection_id)]
        self.sites = [site for site in self.sites if not (site.connection_id == connection_id)]

    def get_site_by_id(self, site_id):
        return [site for site in self.sites if site.id == site_id][0]
