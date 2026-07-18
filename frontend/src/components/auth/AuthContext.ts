"use client";

import { createContext } from "react";
import type { AuthContextValue } from "../../types/session";

export const AuthContext = createContext<AuthContextValue | null>(null);
