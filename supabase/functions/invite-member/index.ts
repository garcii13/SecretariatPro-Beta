import { createClient, type User } from "https://esm.sh/@supabase/supabase-js@2.118.0";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
};

const json = (body: Record<string, unknown>, status = 200) => new Response(JSON.stringify(body), {
  status,
  headers: { ...cors, "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
});

async function findUserByEmail(admin: Pick<ReturnType<typeof createClient>, "auth">, email: string): Promise<User | null> {
  for (let page = 1; page <= 20; page += 1) {
    const { data, error } = await admin.auth.admin.listUsers({ page, perPage: 1000 });
    if (error) throw error;
    const found = data.users.find((user) => String(user.email || "").toLowerCase() === email);
    if (found) return found;
    if (data.users.length < 1000) return null;
  }
  throw new Error("El directorio de usuarios es demasiado grande para completar la búsqueda");
}

Deno.serve(async (request) => {
  if (request.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (request.method !== "POST") return json({ ok: false, error: "Método no permitido" }, 405);

  try {
    const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
    const anonKey = Deno.env.get("SUPABASE_ANON_KEY") || Deno.env.get("SUPABASE_PUBLISHABLE_KEY") || "";
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
    const authorization = request.headers.get("Authorization") || "";
    if (!authorization.startsWith("Bearer ")) return json({ ok: false, error: "Debes iniciar sesión" }, 401);
    if (!supabaseUrl || !anonKey || !serviceKey) return json({ ok: false, error: "La función no está configurada" }, 500);

    const body = await request.json();
    const workspaceId = String(body.workspace_id || "").trim();
    const email = String(body.email || "").trim().toLowerCase();
    const role = String(body.role || "producer").trim().toLowerCase();
    if (!workspaceId) return json({ ok: false, error: "Falta el espacio de trabajo" }, 400);
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return json({ ok: false, error: "Introduce un correo válido" }, 400);
    if (!["producer", "competition_manager"].includes(role)) return json({ ok: false, error: "Rol no válido" }, 400);

    const callerClient = createClient(supabaseUrl, anonKey, {
      global: { headers: { Authorization: authorization } },
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data: userData, error: userError } = await callerClient.auth.getUser();
    if (userError || !userData.user) return json({ ok: false, error: "La sesión ha caducado" }, 401);
    const { data: allowed, error: roleError } = await callerClient.rpc("sp_has_workspace_role", {
      target_workspace: workspaceId,
      accepted_roles: ["owner", "competition_manager"],
    });
    if (roleError) throw roleError;
    if (!allowed) return json({ ok: false, error: "Tu rol no permite invitar miembros" }, 403);

    const admin = createClient(supabaseUrl, serviceKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    let target = await findUserByEmail(admin, email);
    let invited = false;
    if (!target) {
      const portalUrl = String(Deno.env.get("PROFILE_PORTAL_URL") || "").trim();
      if (!portalUrl.startsWith("https://")) return json({ ok: false, error: "El portal de perfiles no está configurado" }, 500);
      const displayName = email.split("@", 1)[0];
      const { data, error } = await admin.auth.admin.inviteUserByEmail(email, {
        redirectTo: portalUrl,
        data: { display_name: displayName, invited_workspace_id: workspaceId },
      });
      if (error) throw error;
      target = data.user;
      invited = true;
    }
    if (!target) throw new Error("Supabase no pudo crear la cuenta invitada");

    const targetName = String(
      target.user_metadata?.display_name || target.user_metadata?.full_name || email.split("@", 1)[0],
    );
    // The caller JWT is checked again inside the atomic database operation.
    // Existing memberships (including owner/suspended) are returned unchanged.
    const { data: membershipResult, error: membershipError } = await callerClient.rpc("sp_invite_workspace_member", {
      p_workspace: workspaceId, p_user: target.id, p_role: role,
    });
    if (membershipError) throw membershipError;
    const membership = membershipResult?.membership;
    if (!membership) throw new Error("La invitación no devolvió una membresía válida");

    const { error: directoryError } = await admin.from("scoreboard_operators").upsert({
      id: target.id,
      email,
      display_name: targetName,
      workspace_id: workspaceId,
    }, { onConflict: "id", ignoreDuplicates: true });
    if (directoryError) console.warn("No se pudo sincronizar scoreboard_operators", directoryError.message);

    return json({
      ok: true,
      invited,
      already_pending: !invited && membership.status === "invited",
      already_member: membershipResult.created === false,
      user_id: target.id,
      email,
      display_name: targetName,
      role: membership.role,
      status: membership.status,
    });
  } catch (error) {
    console.error(error);
    return json({ ok: false, error: error instanceof Error ? error.message : "No se pudo enviar la invitación" }, 400);
  }
});
