from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Identity, Integer, String, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class CompanyRole(PyEnum):
    """Role a user can have within a company."""
    company_admin = "company_admin"
    contributor = "contributor"
    read_only = "read_only"


class MembershipStatus(PyEnum):
    """Status of a user's membership in a company."""
    active = "active"
    invited = "invited"
    disabled = "disabled"


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

    # Global Admin (Phase 1) — when True, the user bypasses per-company /
    # per-portfolio access checks at the resolver and module-permission layers.
    # Distinct from is_system_user (which is reserved for the internal
    # automation account). Granted via /api/admin/global-admins or the
    # `scripts/grant_global_admin.py` CLI. See ff19 migration for safeguards.
    is_global_admin = Column(Boolean, default=False, nullable=False, server_default="false")

    @property
    def has_platform_bypass(self) -> bool:
        """True when the user bypasses per-company authorization checks.

        Used by the canonical authorization layer (access_resolver,
        permission_guards, the various authorization/* helpers, and
        routers that gate read/write on platform-wide privilege).

        - is_system_user: internal automation account (created by initial setup).
        - is_global_admin: human users with platform-wide privilege for
          testing, validation, and support (Phase 1 of the Global Admin
          feature). See ff19 migration and /api/admin/global-admins.
        """
        return bool(self.is_system_user) or bool(self.is_global_admin)

    # relationships
    parent_company = relationship("Company", back_populates="users", foreign_keys=[parent_company_id])
    role = relationship("Role", back_populates="users")
    # site is the primary entity access given to
    sites = relationship(
        "Site",
        secondary="user_projects",
        primaryjoin="User.id == foreign(UserProject.user_id)",
        secondaryjoin="foreign(UserProject.site_id) == Site.id",
        overlaps="_allowed_users,project_memberships,member_users"
    )
    # have companies as well to minimize efforts for company-related APIs serving
    companies = relationship(
        "Company",
        secondary="user_projects",
        primaryjoin="User.id == foreign(UserProject.user_id)",
        secondaryjoin="foreign(UserProject.company_id) == Company.id",
        viewonly=True,
        overlaps="sites,_allowed_users,project_memberships,member_users"
    )
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
    edited_document_keys = relationship(
        "DocumentKey", back_populates="editor", foreign_keys="DocumentKey.editor_id"
    )
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
    
    company_memberships = relationship(
        "UserCompanyAccess",
        back_populates="user",
        foreign_keys="UserCompanyAccess.user_id"
    )
    
    project_memberships = relationship(
        "UserProject",
        back_populates="user",
        foreign_keys="UserProject.user_id"
    )
    
    portfolio_access = relationship(
        "UserPortfolioAccess",
        back_populates="user",
        foreign_keys="UserPortfolioAccess.user_id"
    )

    def get_limited_sites_ids(self):
        """Return IDs of sites user has access to. If user is system - return None"""
        return None if self.has_platform_bypass else {site.id for site in self.sites}

    def get_limited_companies_ids(self):
        """Return IDs of companies user has access to. If user is system - return None"""
        return None if self.has_platform_bypass else {company.id for company in self.companies}


class UserProject(Base):
    """Project-level user access - gives user access to a specific project/site."""
    __tablename__ = "user_projects"

    __table_args__ = (
        UniqueConstraint('user_id', 'site_id', name='uq_user_project_access'),
        Index('ix_user_project_site_id', 'site_id'),
        Index('ix_user_project_user_id', 'user_id'),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(CompanyRole), nullable=False, default=CompanyRole.contributor)
    status = Column(Enum(MembershipStatus), nullable=False, default=MembershipStatus.active)

    created_at = Column(DateTime, server_default=utcnow())
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    user = relationship("User", back_populates="project_memberships", foreign_keys=[user_id], overlaps="sites,companies,_allowed_users")
    site = relationship("Site", back_populates="member_users", overlaps="sites,_allowed_users")
    company = relationship("Company", overlaps="companies,_allowed_users")
    created_by = relationship("User", foreign_keys=[created_by_user_id])


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


class UserCompanyAccess(Base):
    """First-class company membership for users - independent of project assignments."""
    __tablename__ = "user_company_access"
    
    __table_args__ = (
        UniqueConstraint('user_id', 'company_id', name='uq_user_company_access'),
        Index('ix_user_company_access_company_id', 'company_id'),
        Index('ix_user_company_access_user_id', 'user_id'),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(CompanyRole), nullable=False, default=CompanyRole.contributor)
    status = Column(Enum(MembershipStatus), nullable=False, default=MembershipStatus.active)
    created_from_portfolio = Column(Boolean, default=False)
    
    role_profile_key = Column(String(50), ForeignKey("role_profiles.key", ondelete="SET NULL"), nullable=True)
    module_permissions = Column(JSONB, nullable=True)
    dashboard_key = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, server_default=utcnow())
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    user = relationship("User", back_populates="company_memberships", foreign_keys=[user_id])
    company = relationship("Company", back_populates="member_users")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    role_profile = relationship("RoleProfile", foreign_keys=[role_profile_key])


class UserPortfolioAccess(Base):
    """Portfolio-level user access - gives user access to companies within a portfolio hub."""
    __tablename__ = "user_portfolio_access"
    
    __table_args__ = (
        UniqueConstraint('user_id', 'portfolio_hub_company_id', name='uq_user_portfolio_access_per_hub'),
        Index('ix_user_portfolio_access_user_id', 'user_id'),
        Index('ix_user_portfolio_access_hub_id', 'portfolio_hub_company_id'),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    portfolio_hub_company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True
    )
    role = Column(Enum(CompanyRole), nullable=False, default=CompanyRole.contributor)
    status = Column(Enum(MembershipStatus), nullable=False, default=MembershipStatus.active)
    
    created_at = Column(DateTime, server_default=utcnow())
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    user = relationship("User", back_populates="portfolio_access", foreign_keys=[user_id])
    portfolio_hub_company = relationship("Company", foreign_keys=[portfolio_hub_company_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
