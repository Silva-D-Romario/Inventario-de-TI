import { useEffect, useState } from 'react'

import { download, fetchBlob } from '../../../lib/api'
import type { Asset } from '../../../lib/types'

export function AssetQrCard({ asset }: { asset: Asset }) {
  const [imageUrl, setImageUrl] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    let objectUrl = ''
    setError('')
    void fetchBlob(asset.qr_code_url)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setImageUrl(objectUrl)
      })
      .catch(() => { if (active) setError('Não foi possível carregar o QR Code.') })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [asset.qr_code_url])

  return (
    <article className="panel qr-card">
      <div><p className="eyebrow">IDENTIFICAÇÃO</p><h2>QR Code</h2></div>
      {imageUrl ? <img src={imageUrl} alt={`QR Code do ativo ${asset.asset_tag}`} /> : <div className="qr-placeholder">{error || 'Carregando...'}</div>}
      <button className="secondary-button" onClick={() => download(asset.qr_code_url, `${asset.asset_tag}-qrcode.png`)}>Baixar etiqueta</button>
    </article>
  )
}
