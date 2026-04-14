import type { TableSchema } from '../types/api'

type Props = {
  tables: TableSchema[] | null
  loading: boolean
  onRefresh: () => void
}

export function SchemaSidebar({ tables, loading, onRefresh }: Props) {
  // Nhóm bảng theo Database
  const groupedTables = tables?.reduce((acc: Record<string, TableSchema[]>, t) => {
    const db = t.db_name || 'Default'
    if (!acc[db]) acc[db] = []
    acc[db].push(t)
    return acc
  }, {})

  return (
    <aside className="sidebar schema-sidebar">
      <div className="sidebar-header">
        <span>Lược đồ</span>
        <button type="button" className="btn small secondary" onClick={onRefresh} disabled={loading}>
          {loading ? '…' : 'Tải lại'}
        </button>
      </div>
      {!tables?.length ? (
        <p className="empty-hint">{loading ? 'Đang tải…' : 'Chưa có dữ liệu. Bấm Tải lại.'}</p>
      ) : (
        <div className="schema-scrollable">
          {Object.entries(groupedTables || {}).map(([db, dbTables]) => (
            <div key={db} className="schema-db-group">
              <h4 className="db-title">📦 {db}</h4>
              <ul className="schema-tables">
                {dbTables.map((t) => (
                  <li key={t.table_name} className="schema-table">
                    <details>
                      <summary>{t.table_name}</summary>
                      {t.primary_keys.length ? (
                        <p className="pk-line">PK: {t.primary_keys.join(', ')}</p>
                      ) : null}
                      <ul className="column-list">
                        {t.columns.map((c) => (
                          <li key={c.name} title={c.comment || undefined}>
                            <code>{c.name}</code> <span className="col-type">{c.type}</span>
                            {!c.nullable ? <span className="badge">NOT NULL</span> : null}
                            {c.comment ? <span className="col-comment"> // {c.comment}</span> : null}
                          </li>
                        ))}
                      </ul>
                      {t.foreign_keys.length ? (
                        <ul className="fk-list">
                          {t.foreign_keys.map((fk, i) => (
                            <li key={i}>
                              {fk.constrained_columns.join(',')} → {fk.referred_table}(
                              {fk.referred_columns.join(',')})
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </details>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </aside>
  )
}
