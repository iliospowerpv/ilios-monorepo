import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEntityContext } from '../../../contexts/entityContext';
import type { ProjectInfo } from './ProjectPicker';
import type { FocusType } from '../../../utils/navigation/taskDestinationResolver';

export type ProjectHubTab = 'overview' | 'data-room' | 'om' | 'finance' | 'tasks' | 'reporting';

export interface FocusParams {
  focusType: FocusType;
  focusId: number | null;
}

interface UseProjectNavigationReturn {
  isPickerOpen: boolean;
  openPicker: () => void;
  closePicker: () => void;
  navigateToProjectHub: (projectId: number, tab?: ProjectHubTab, focus?: FocusParams) => void;
  navigateWithFallback: (
    siteId: number | null,
    tab?: ProjectHubTab,
    focus?: FocusParams
  ) => void;
  ensureProjectSelected: (tab?: ProjectHubTab) => void;
  handleProjectSelect: (project: ProjectInfo) => void;
  pendingTab: ProjectHubTab | null;
  pendingFocus: FocusParams | null;
}

export const useProjectNavigation = (): UseProjectNavigationReturn => {
  const navigate = useNavigate();
  const { currentProject, setCurrentProject } = useEntityContext();
  const [isPickerOpen, setIsPickerOpen] = useState(false);
  const [pendingTab, setPendingTab] = useState<ProjectHubTab | null>(null);
  const [pendingFocus, setPendingFocus] = useState<FocusParams | null>(null);

  const openPicker = useCallback(() => {
    setIsPickerOpen(true);
  }, []);

  const closePicker = useCallback(() => {
    setIsPickerOpen(false);
    setPendingTab(null);
    setPendingFocus(null);
  }, []);

  const navigateToProjectHub = useCallback(
    (projectId: number, tab: ProjectHubTab = 'overview', focus?: FocusParams) => {
      const tabPath = tab === 'overview' ? '' : `/${tab}`;
      let url = `/project-hub/projects/${projectId}${tabPath}`;

      if (focus?.focusType && focus?.focusId) {
        url += `?focusType=${focus.focusType}&focusId=${focus.focusId}`;
      }

      navigate(url);
    },
    [navigate]
  );

  const navigateWithFallback = useCallback(
    (siteId: number | null, tab: ProjectHubTab = 'tasks', focus?: FocusParams) => {
      if (siteId) {
        navigateToProjectHub(siteId, tab, focus);
      } else if (currentProject) {
        navigateToProjectHub(currentProject.id, tab, focus);
      } else {
        setPendingTab(tab);
        setPendingFocus(focus || null);
        setIsPickerOpen(true);
      }
    },
    [currentProject, navigateToProjectHub]
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
      navigateToProjectHub(project.id, targetTab, pendingFocus || undefined);
      setIsPickerOpen(false);
      setPendingTab(null);
      setPendingFocus(null);
    },
    [setCurrentProject, pendingTab, pendingFocus, navigateToProjectHub]
  );

  return {
    isPickerOpen,
    openPicker,
    closePicker,
    navigateToProjectHub,
    navigateWithFallback,
    ensureProjectSelected,
    handleProjectSelect,
    pendingTab,
    pendingFocus
  };
};
