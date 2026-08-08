import clientesImportadosRaw from "@/lib/clientes-import.json";

type ClienteImportadoRaw = { tags: string[] };

/**
 * Grupo de Cliente já é 100% real (backend) — ver lib/diretorioGruposCliente.ts. O que
 * sobrou aqui é só a resolução nome -> codigoInterno usada por clientes-mock.ts, que ainda
 * é mock nesta entrega: a planilha importada guarda o NOME do grupo, e `Cliente.tagIds`
 * precisa guardar uma referência estável.
 *
 * O valor devolvido é o mesmo id que o mock antigo gerava (ex. "grupo-grupo-bretas") — que
 * o seed do backend preservou como `codigoInterno` do grupo real (ver
 * backend/app/cli/seed_grupos_cliente.py), então essas referências continuam resolvendo via
 * lib/referencias.ts. Este arquivo sai quando Cliente virar real.
 */

function slugify(nome: string): string {
  return nome
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

const nomesGruposImportados = new Set(
  (clientesImportadosRaw as ClienteImportadoRaw[]).flatMap((cliente) => cliente.tags ?? []),
);

export function resolveTagIdPorNome(nomeLivre: string): string {
  const normalizado = nomeLivre.trim();
  if (!nomesGruposImportados.has(normalizado)) return "";
  return `grupo-${slugify(normalizado)}`;
}
