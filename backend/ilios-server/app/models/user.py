from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Identity, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    parent_company_id = Column(Integer, ForeignKey("companies.id", ondelete="SET NULL"))
    role_id = Column(Integer, ForeignKey("roles.id", ondelete="SET NULL"))
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String, nullable=False)
    hashed_password = Column(String, nullable=True)
    is_registered = Column(Boolean, default=False)

    # setting up the server_default value, that will be filled on the database side
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    # system user, similar to super-admin in Django
    is_system_user = Column(Boolean, default=False)

    # relationships
    parent_company = relationship("Company", back_populates="users")
    role = relationship("Role", back_populates="users")
    # site is the primary entity access given to
    sites = relationship("Site", secondary="user_projects", overlaps="_allowed_users")
    # have companies as well to minimize efforts for company-related APIs serving
    companies = relationship("Company", secondary="user_projects", viewonly=True)
    # have files and attachments as user is an author
    files = relationship("File", back_populates="user")
    attachments = relationship("Attachment", back_populates="user")
    site_visit_uploads = relationship("SiteVisitUpload", back_populates="user")
    # tasks
    assigned_tasks = relationship("Task", back_populates="assignee", primaryjoin="User.id == Task.assignee_id")
    created_tasks = relationship("Task", back_populates="creator", primaryjoin="User.id == Task.creator_id")
    created_site_visits = relationship(
        "SiteVisit", back_populates="creator", primaryjoin="User.id == SiteVisit.creator_id"
    )
    # edited document keys
    edited_document_keys = relationship("DocumentKey", back_populates="editor")
    # notifications
    triggered_notifications = relationship(
        "Notification", back_populates="actor", primaryjoin="User.id == Notification.actor_id"
    )
    received_notifications = relationship(
        "Notification", back_populates="recipient", primaryjoin="User.id == Notification.recipient_id"
    )
    # assigned to approve documents
    approving_documents = relationship("Document", back_populates="approver")
    # mentions in comments
    mentions = relationship("CommentMention", back_populates="user")

    invitation = relationship("UserInvitation", back_populates="user")
    password_recovery = relationship("UserPasswordRecovery", back_populates="user")
    sessions = relationship("Session", back_populates="user")

    def get_limited_sites_ids(self):
        """Return IDs of sites user has access to. If user is system - return None"""
        return None if self.is_system_user else {site.id for site in self.sites}

    def get_limited_companies_ids(self):
        """Return IDs of companies user has access to. If user is system - return None"""
        return None if self.is_system_user else {company.id for company in self.companies}


class UserProject(Base):
    __tablename__ = "user_projects"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())


class UserPasswordDeeplinkBase:
    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    token = Column(String)
    expires_at = Column(DateTime)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())


class UserInvitation(Base, UserPasswordDeeplinkBase):
    __tablename__ = "user_invitations"

    user = relationship("User", back_populates="invitation")


class UserPasswordRecovery(Base, UserPasswordDeeplinkBase):
    __tablename__ = "user_password_recovery"

    user = relationship("User", back_populates="password_recovery")
