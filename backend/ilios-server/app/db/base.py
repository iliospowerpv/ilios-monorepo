# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base
from app.models.alert import Alert
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.board import Board, BoardRelatedEntity, BoardStatus
from app.models.chatbot import ChatBotConversation
from app.models.comment import Comment
from app.models.company import Company
from app.models.device import Device
from app.models.device_document import DeviceDocument
from app.models.document import Document
from app.models.file import File
from app.models.internal_configuration import InternalConfiguration
from app.models.notification import Notification
from app.models.role import Role
from app.models.session import Session
from app.models.site import Site
from app.models.site_visit import SiteVisit
from app.models.sv_uploads import SiteVisitUpload
from app.models.task import Task
from app.models.telemetry import DASConnection, TelemetrySiteMapping
from app.models.user import User
