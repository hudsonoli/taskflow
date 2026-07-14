/**
 * Uppercase automático para campos de identificação (nome fantasia, razão
 * social, sigla) — aplicado durante a digitação, para que o valor já seja
 * armazenado em caixa alta. Nunca usar em e-mail, site, PIX, banco, login
 * ou senha. Reutilizável por outras entidades (Usuários, Fornecedores)
 * quando adotarem o mesmo padrão de cadastro.
 */
export function toUppercaseField(value: string): string {
  return value.toLocaleUpperCase("pt-BR");
}
