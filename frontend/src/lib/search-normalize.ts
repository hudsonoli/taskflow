/**
 * Normalização compartilhada para busca textual em telas de cadastro.
 * Reutilizável por outras entidades (Fornecedores, Usuários, Grupos de
 * Clientes, etc.) sem acoplar a lógica a uma tela específica.
 */
export function normalizeSearchText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .trim()
    .replace(/\s+/g, " ");
}

/**
 * Para documentos/códigos (CNPJ, CPF, código interno): remove também
 * pontuação, permitindo comparar "12345678000190" com "12.345.678/0001-90".
 */
export function normalizeSearchToken(value: string): string {
  return normalizeSearchText(value).replace(/[^a-z0-9]/g, "");
}
