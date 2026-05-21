import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { notesApi } from "../services/api";
import { useAuth } from "./AuthContext";
import { useToast } from "./ToastContext";

const NoteContext = createContext(null);
const NOTES_CACHE_KEY = "concept_tree_notes_cache";

const readNotesCache = () => {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(NOTES_CACHE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed?.notes) ? parsed.notes : [];
  } catch {
    return [];
  }
};

const writeNotesCache = (notes) => {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      NOTES_CACHE_KEY,
      JSON.stringify({ notes: Array.isArray(notes) ? notes : [], savedAt: Date.now() }),
    );
  } catch {
    // localStorage may be unavailable; notes still work for this session.
  }
};

export const useNoteContext = () => {
  const context = useContext(NoteContext);
  if (!context) {
    throw new Error("useNoteContext must be used within a NoteProvider");
  }
  return context;
};

export const NoteProvider = ({ children }) => {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const toast = useToast();

  const [allNotes, setAllNotes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    const loadNotes = async () => {
      if (authLoading) return;

      setIsLoading(true);
      try {
        if (isAuthenticated) {
          const notesList = await notesApi.list();
          const nextNotes = Array.isArray(notesList) ? notesList : (notesList?.notes || []);
          setAllNotes(nextNotes);
          writeNotesCache(nextNotes);
          setLoadError(null);
        } else {
          setAllNotes([]);
          writeNotesCache([]);
          setLoadError(null);
        }
      } catch (error) {
        const cachedNotes = readNotesCache();
        setAllNotes(cachedNotes);
        setLoadError(error);
        toast.error(
          cachedNotes.length > 0
            ? "加载笔记失败，已显示本地缓存"
            : "加载笔记失败，请稍后重试",
        );
      } finally {
        setIsLoading(false);
      }
    };

    loadNotes();
  }, [authLoading, isAuthenticated, toast]);

  const actions = useMemo(
    () => ({
      setAllNotes,
      async addNote(planId, nodeId, content) {
        try {
          const newNote = await notesApi.create(planId, nodeId, content);
          setAllNotes((prev) => {
            const next = [newNote, ...prev];
            writeNotesCache(next);
            return next;
          });
          return newNote;
        } catch (error) {
          toast.error("添加笔记失败");
          throw error;
        }
      },
      async updateNote(noteId, content) {
        try {
          const updatedNote = await notesApi.update(noteId, content);
          setAllNotes((prev) => {
            const next = prev.map((note) =>
              note.id === noteId ? { ...note, ...updatedNote, content } : note,
            );
            writeNotesCache(next);
            return next;
          });
          return updatedNote;
        } catch (error) {
          toast.error("更新笔记失败");
          throw error;
        }
      },
      async deleteNote(noteId) {
        try {
          await notesApi.delete(noteId);
          setAllNotes((prev) => {
            const next = prev.filter((note) => note.id !== noteId);
            writeNotesCache(next);
            return next;
          });
        } catch (error) {
          toast.error("删除笔记失败");
          throw error;
        }
      },
    }),
    [toast],
  );

  const value = useMemo(
    () => ({
      allNotes,
      isLoading,
      loadError,
      actions,
    }),
    [actions, allNotes, isLoading, loadError],
  );

  return <NoteContext.Provider value={value}>{children}</NoteContext.Provider>;
};
