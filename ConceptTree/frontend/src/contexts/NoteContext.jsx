import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { notesApi } from "../services/api";
import { useAuth } from "./AuthContext";
import { useToast } from "./ToastContext";

const NoteContext = createContext(null);

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
  const showErrorToast = toast.error;

  const [allNotes, setAllNotes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadNotes = async () => {
      if (authLoading) return;

      setIsLoading(true);
      try {
        if (isAuthenticated) {
          const notesList = await notesApi.list();
          setAllNotes(
            Array.isArray(notesList) ? notesList : (notesList?.notes || []),
          );
        } else {
          setAllNotes([]);
        }
      } catch (error) {
        showErrorToast("加载笔记失败，请刷新后重试");
      } finally {
        setIsLoading(false);
      }
    };

    loadNotes();
  }, [authLoading, isAuthenticated, showErrorToast]);

  const actions = useMemo(
    () => ({
      setAllNotes,
      async addNote(planId, nodeId, content) {
        try {
          const newNote = await notesApi.create(planId, nodeId, content);
          setAllNotes((prev) => [newNote, ...prev]);
          return newNote;
        } catch (error) {
          showErrorToast(error?.message || "添加笔记失败");
          throw error;
        }
      },
      async updateNote(noteId, content) {
        try {
          const updatedNote = await notesApi.update(noteId, content);
          setAllNotes((prev) =>
            prev.map((note) =>
              note.id === noteId ? { ...note, ...updatedNote, content } : note,
            ),
          );
          return updatedNote;
        } catch (error) {
          showErrorToast(error?.message || "更新笔记失败");
          throw error;
        }
      },
      async deleteNote(noteId) {
        try {
          await notesApi.delete(noteId);
          setAllNotes((prev) => prev.filter((note) => note.id !== noteId));
        } catch (error) {
          showErrorToast(error?.message || "删除笔记失败");
          throw error;
        }
      },
    }),
    [showErrorToast],
  );

  const value = useMemo(
    () => ({
      allNotes,
      isLoading,
      actions,
    }),
    [actions, allNotes, isLoading],
  );

  return <NoteContext.Provider value={value}>{children}</NoteContext.Provider>;
};
