import React, { createContext, useContext, useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export type EntityLevel = 'portfolio' | 'company' | 'project';

export interface EntityInfo {
  id: number;
  name: string;
}

interface EntityContextType {
  currentLevel: EntityLevel;
  currentCompany: EntityInfo | null;
  currentProject: EntityInfo | null;
  currentModule: string | null;
  setCurrentCompany: (company: EntityInfo | null) => void;
  setCurrentProject: (project: EntityInfo | null) => void;
  setCurrentModule: (module: string | null) => void;
  navigateToLevel: (level: EntityLevel) => void;
  getModuleBasePath: (module: string) => string;
}

const EntityContext = createContext<EntityContextType | undefined>(undefined);

const STORAGE_KEY = 'ilios_entity_context';

interface StoredContext {
  company: EntityInfo | null;
  project: EntityInfo | null;
}

const loadStoredContext = (): StoredContext => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch {
    // ignore
  }
  return { company: null, project: null };
};

const saveContext = (context: StoredContext): void => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(context));
  } catch {
    // ignore
  }
};

export const EntityContextProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const storedContext = loadStoredContext();
  const [currentCompany, setCurrentCompanyState] = useState<EntityInfo | null>(storedContext.company);
  const [currentProject, setCurrentProjectState] = useState<EntityInfo | null>(storedContext.project);
  const [currentModule, setCurrentModule] = useState<string | null>(null);

  const currentLevel = useMemo((): EntityLevel => {
    const path = location.pathname;
    if (path.includes('/sites/') || path.includes('/projects/')) {
      return 'project';
    }
    if (path.includes('/companies/')) {
      return 'company';
    }
    return 'portfolio';
  }, [location.pathname]);

  useEffect(() => {
    const path = location.pathname;
    if (path.startsWith('/asset-management')) {
      setCurrentModule('asset-management');
    } else if (path.startsWith('/operations-and-maintenance')) {
      setCurrentModule('operations-and-maintenance');
    } else if (path.startsWith('/due-diligence')) {
      setCurrentModule('due-diligence');
    } else if (path.startsWith('/finance')) {
      setCurrentModule('finance');
    } else if (path.startsWith('/sales')) {
      setCurrentModule('sales');
    } else if (path.startsWith('/reports')) {
      setCurrentModule('reports');
    } else if (path.startsWith('/dashboard')) {
      setCurrentModule('dashboard');
    } else if (path.startsWith('/my-portfolio')) {
      setCurrentModule('my-portfolio');
    } else {
      setCurrentModule(null);
    }
  }, [location.pathname]);

  const setCurrentCompany = useCallback(
    (company: EntityInfo | null) => {
      setCurrentCompanyState(company);
      if (!company) {
        setCurrentProjectState(null);
      }
      saveContext({ company, project: company ? currentProject : null });
    },
    [currentProject]
  );

  const setCurrentProject = useCallback(
    (project: EntityInfo | null) => {
      setCurrentProjectState(project);
      saveContext({ company: currentCompany, project });
    },
    [currentCompany]
  );

  const getModuleBasePath = useCallback((module: string): string => {
    switch (module) {
      case 'asset-management':
        return '/asset-management';
      case 'operations-and-maintenance':
        return '/operations-and-maintenance';
      case 'due-diligence':
        return '/due-diligence';
      case 'finance':
        return '/finance';
      case 'reports':
        return '/reports';
      default:
        return '/dashboard';
    }
  }, []);

  const navigateToLevel = useCallback(
    (level: EntityLevel) => {
      const module = currentModule || 'asset-management';
      const basePath = getModuleBasePath(module);

      switch (level) {
        case 'portfolio':
          navigate(basePath);
          break;
        case 'company':
          if (currentCompany) {
            navigate(`${basePath}/companies/${currentCompany.id}`);
          }
          break;
        case 'project':
          if (currentCompany && currentProject) {
            navigate(`${basePath}/companies/${currentCompany.id}/sites/${currentProject.id}`);
          }
          break;
      }
    },
    [currentModule, currentCompany, currentProject, navigate, getModuleBasePath]
  );

  const value = useMemo(
    () => ({
      currentLevel,
      currentCompany,
      currentProject,
      currentModule,
      setCurrentCompany,
      setCurrentProject,
      setCurrentModule,
      navigateToLevel,
      getModuleBasePath
    }),
    [
      currentLevel,
      currentCompany,
      currentProject,
      currentModule,
      setCurrentCompany,
      setCurrentProject,
      navigateToLevel,
      getModuleBasePath
    ]
  );

  return <EntityContext.Provider value={value}>{children}</EntityContext.Provider>;
};

export const useEntityContext = (): EntityContextType => {
  const context = useContext(EntityContext);
  if (context === undefined) {
    throw new Error('useEntityContext must be used within an EntityContextProvider');
  }
  return context;
};
