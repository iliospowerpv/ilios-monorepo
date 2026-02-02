import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEntityContext } from '../../../contexts/entityContext';
import type { ProjectInfo } from './ProjectPicker';

export type ProjectHubTab = 'overview' | 'data-room' | 'om' | 'finance' | 'tasks' | 'reporting';

interface UseProjectNavigationReturn {
  isPickerOpen: boolean;
  openPicker: () => void;
  closePicker: () => void;
  navigateToProjectHub: (projectId: number, tab?: ProjectHubTab) => void;
  ensureProjectSelected: (tab?: ProjectHubTab) => void;
  handleProjectSelect: (project: ProjectInfo) => void;
  pendingTab: ProjectHubTab | null;
}

export const useProjectNavigation = (): UseProjectNavigationReturn => {
  const navigate = useNavigate();
  const { currentProject, setCurrentProject } = useEntityContext();
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [pendingTab, setPendingTab] = useState<ProjectHubTab | null>(null);

  const openPicker = useCallback(() => {
    setIsPickerOpen(true);
  }, []);

  const closePicker = useCallback(() => {
    setIsPickerOpen(false);
    setPendingTab(null);
  }, []);

  const navigateToProjectHub = useCallback(
    (projectId: number, tab: ProjectHubTab = 'overview') => {
      const tabPath = tab === 'overview' ? '' : `/${tab}`;
      navigate(`/project-hub/projects/${projectId}${tabPath}`);
    },
    [navigate]
  );

  const ensureProjectSelected = useCallback(
    (tab: ProjectHubTab = 'overview') => {
      if (currentProject) {
        navigateToProjectHub(currentProject.id, tab);
      } else {
        setPendingTab(tab);
        setIsPickerOpen(true);
      }
    },
    [currentProject, navigateToProjectHub]
  );

  const handleProjectSelect = useCallback(
    (project: ProjectInfo) => {
      setCurrentProject({ id: project.id, name: project.name });
      const targetTab = pendingTab || 'overview';
      navigateToProjectHub(project.id, targetTab);
      setIsPickerOpen(false);
      setPendingTab(null);
    },
    [setCurrentProject, pendingTab, navigateToProjectHub]
  );

  return {
    isPickerOpen,
    openPicker,
    closePicker,
    navigateToProjectHub,
    ensureProjectSelected,
    handleProjectSelect,
    pendingTab
  };
};
