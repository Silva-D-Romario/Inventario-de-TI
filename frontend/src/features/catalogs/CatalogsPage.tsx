import { PageHeader } from '../../components/common/PageHeader'
import { useAuth } from '../auth/AuthContext'
import { ReferenceManager } from './ReferenceManager'

export function CatalogsPage() {
  const { user } = useAuth()
  if (user?.role !== 'ADMIN') {
    return <section className="state-box error"><strong>Acesso restrito</strong><p>Somente administradores podem alterar os cadastros auxiliares.</p></section>
  }

  return (
    <>
      <PageHeader eyebrow="ADMINISTRAÇÃO" title="Cadastros auxiliares" description="Mantenha as opções utilizadas na classificação dos ativos." />
      <section className="catalog-grid">
        <ReferenceManager title="Categorias" endpoint="categories" fields={[{ key: 'name', label: 'Nome', placeholder: 'Notebook', required: true }, { key: 'description', label: 'Descrição', placeholder: 'Equipamentos portáteis' }]} />
        <ReferenceManager title="Setores" endpoint="sectors" fields={[{ key: 'name', label: 'Nome', placeholder: 'Tecnologia da Informação', required: true }, { key: 'location', label: 'Localização', placeholder: 'Bloco A · Sala 12' }]} />
        <ReferenceManager title="Status" endpoint="statuses" fields={[{ key: 'name', label: 'Nome', placeholder: 'Disponível', required: true }, { key: 'code', label: 'Código', placeholder: 'available', required: true }, { key: 'color', label: 'Cor', type: 'color', required: true }]} />
      </section>
    </>
  )
}
