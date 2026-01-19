/**
 * Hook for managing task selection state for bulk operations.
 */

import { useState, useCallback, useMemo } from "react";

interface UseTaskSelectionReturn {
  selectedIds: Set<string>;
  isSelected: (id: string) => boolean;
  toggle: (id: string) => void;
  selectAll: (ids: string[]) => void;
  clearSelection: () => void;
  selectCount: number;
  hasSelection: boolean;
}

export function useTaskSelection(): UseTaskSelectionReturn {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const isSelected = useCallback(
    (id: string) => selectedIds.has(id),
    [selectedIds]
  );

  const toggle = useCallback((id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectAll = useCallback((ids: string[]) => {
    setSelectedIds(new Set(ids));
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const selectCount = selectedIds.size;
  const hasSelection = selectCount > 0;

  return {
    selectedIds,
    isSelected,
    toggle,
    selectAll,
    clearSelection,
    selectCount,
    hasSelection,
  };
}
