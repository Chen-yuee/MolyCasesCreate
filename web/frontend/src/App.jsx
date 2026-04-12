import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import DialogList from './pages/DialogList'
import DialogView from './pages/DialogView'

export default function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<DialogList />} />
          <Route path="/dialog/:dialogId" element={<DialogView />} />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  )
}
