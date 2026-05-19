const { contextBridge, ipcRenderer } = require('electron')

// Expose protected methods to renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Window controls
  minimize: () => ipcRenderer.send('window-minimize'),
  maximize: () => ipcRenderer.send('window-maximize'),
  close: () => ipcRenderer.send('window-close'),

  // App info
  getVersion: () => ipcRenderer.invoke('get-app-version'),
  isDev: () => ipcRenderer.invoke('is-dev'),

  // Platform
  platform: process.platform,

  // Dialogs (main process)
  showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options),

  // Events
  onMenuUpload: (callback) => ipcRenderer.on('menu-upload', callback),
  onClearMemory: (callback) => ipcRenderer.on('clear-memory', callback),

  // Remove listeners
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel)
})

// Expose utility functions
contextBridge.exposeInMainWorld('utils', {
  openExternal: (url) => shell.openExternal(url),
  showItemInFolder: (path) => shell.showItemInFolder(path),
  beep: () => require('child_process').exec('echo -ne "\007"') // Simple beep
})

// Auto-setup listeners for renderer
window.addEventListener('DOMContentLoaded', () => {
  // Hook into window controls if present in page
  const originalMinimize = window.electronAPI?.minimize
  // Your custom logic here
})
