/**
 * Hook for persisting filter state in URL params and localStorage.
 */

import { useState, useEffect, useCallback } from "react";
import type { TaskPriority } from "@/types/task";

export type SortOption = "priority" | "created" | "updated" | "name";

interface FilterState {
  searchTerm: string;
  priorityFilter: TaskPriority | "ALL";
  showCompleted: boolean;
  sortBy: SortOption;
}

const STORAGE_KEY = "ralph-dashboard-filters";

function getInitialState(): FilterState {
  // First check URL params
  if (typeof window !== "undefined") {
    const params = new URLSearchParams(window.location.search);
    const search = params.get("search");
    const priority = params.get("priority");
    const showCompleted = params.get("showCompleted");
    const sortBy = params.get("sortBy");

    if (search !== null || priority !== null || showCompleted !== null || sortBy !== null) {
      return {
        searchTerm: search || "",
        priorityFilter: (priority as TaskPriority | "ALL") || "ALL",
        showCompleted: showCompleted !== "false",
        sortBy: (sortBy as SortOption) || "priority",
      };
    }

    // Fall back to localStorage
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        return JSON.parse(stored);
      }
    } catch {
      // Ignore parse errors
    }
  }

  return {
    searchTerm: "",
    priorityFilter: "ALL",
    showCompleted: true,
    sortBy: "priority",
  };
}

function updateURL(state: FilterState) {
  if (typeof window === "undefined") return;

  const params = new URLSearchParams();

  if (state.searchTerm) {
    params.set("search", state.searchTerm);
  }
  if (state.priorityFilter !== "ALL") {
    params.set("priority", state.priorityFilter);
  }
  if (!state.showCompleted) {
    params.set("showCompleted", "false");
  }
  if (state.sortBy !== "priority") {
    params.set("sortBy", state.sortBy);
  }

  const newURL = params.toString()
    ? `${window.location.pathname}?${params.toString()}`
    : window.location.pathname;

  window.history.replaceState({}, "", newURL);
}

function saveToStorage(state: FilterState) {
  if (typeof window === "undefined") return;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore storage errors
  }
}

export function useFilterState() {
  const [state, setState] = useState<FilterState>(getInitialState);

  // Sync to URL and localStorage when state changes
  useEffect(() => {
    updateURL(state);
    saveToStorage(state);
  }, [state]);

  const setSearchTerm = useCallback((searchTerm: string) => {
    setState(prev => ({ ...prev, searchTerm }));
  }, []);

  const setPriorityFilter = useCallback(
    (priorityFilter: TaskPriority | "ALL") => {
      setState(prev => ({ ...prev, priorityFilter }));
    },
    []
  );

  const setShowCompleted = useCallback((showCompleted: boolean) => {
    setState(prev => ({ ...prev, showCompleted }));
  }, []);

  const setSortBy = useCallback((sortBy: SortOption) => {
    setState(prev => ({ ...prev, sortBy }));
  }, []);

  const resetFilters = useCallback(() => {
    setState({
      searchTerm: "",
      priorityFilter: "ALL",
      showCompleted: true,
      sortBy: "priority",
    });
  }, []);

  return {
    ...state,
    setSearchTerm,
    setPriorityFilter,
    setShowCompleted,
    setSortBy,
    resetFilters,
  };
}
