// Supabase client for the frontend (anon key only). The service_role key
// stays in the Node API server.
import { createClient } from "@supabase/supabase-js";

const url  = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

export const supabase =
  url && anon ? createClient(url, anon) : null;
