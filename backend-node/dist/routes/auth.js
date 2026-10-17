import { Router } from "express";
import { z } from "zod";
import { supabase } from "../middleware/supabase.js";
export const authRouter = Router();
const credentials = z.object({
    email: z.string().email(),
    password: z.string().min(8),
});
authRouter.post("/login", async (req, res) => {
    const parsed = credentials.safeParse(req.body);
    if (!parsed.success) {
        return res
            .status(400)
            .json({ error: { code: "BAD_INPUT", message: parsed.error.message } });
    }
    if (!supabase) {
        return res.json({
            session: { access_token: "mock-token-local", token_type: "bearer" },
            user: { id: "local-dev", email: parsed.data.email, role: "admin" }
        });
    }
    const { data, error } = await supabase.auth.signInWithPassword(parsed.data);
    if (error) {
        return res
            .status(401)
            .json({ error: { code: "LOGIN_FAILED", message: error.message } });
    }
    return res.json({ session: data.session, user: data.user });
});
authRouter.post("/logout", async (req, res) => {
    const token = (req.headers.authorization ?? "").replace("Bearer ", "");
    if (!token || !supabase)
        return res.json({ ok: true });
    await supabase.auth.admin.signOut(token).catch(() => undefined);
    return res.json({ ok: true });
});
