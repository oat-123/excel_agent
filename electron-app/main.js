const { app, BrowserWindow, Menu, shell, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const os = require('os')

let flaskProcess = null
let mainWindow = null
let isQuitting = false

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    title: 'J.A.R.V.I.S. Excel Agent',
    icon: path.join(__dirname, 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false // Allow loading from localhost
    },
    frame: true,
    titleBarStyle: 'default',
    backgroundColor: '#05070a',
    show: false, // Show after ready
    alwaysOnTop: false
  })

  // Show when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    if (isDev) mainWindow.webContents.openDevTools()
  })

  // Load Flask app
  mainWindow.loadURL('http://localhost:5000')

  // Handle window close
  mainWindow.on('close', (e) => {
    if (!isQuitting) {
      e.preventDefault()
      mainWindow.hide()
      // Show tray notification (simplified)
    }
  })

  // Create application menu
  const menuTemplate = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Upload File',
          accelerator: 'CmdOrCtrl+O',
          click: () => mainWindow.webContents.send('menu-upload')
        },
        { type: 'separator' },
        {
          label: 'Quit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => quitApp()
        }
      ]
    },
    {
      label: 'View',
      submenu: [
        { label: 'Reload', accelerator: 'CmdOrCtrl+R', role: 'reload' },
        { label: 'Force Reload', accelerator: 'CmdOrCtrl+Shift+R', role: 'forceReload' },
        { type: 'separator' },
        { label: 'Actual Size', role: 'resetZoom' },
        { label: 'Zoom In', accelerator: 'CmdOrCtrl+Plus', role: 'zoomIn' },
        { label: 'Zoom Out', accelerator: 'CmdOrCtrl+-', role: 'zoomOut' },
        { type: 'separator' },
        {
          label: 'Toggle Always on Top',
          click: () => {
            const isTop = mainWindow.isAlwaysOnTop()
            mainWindow.setAlwaysOnTop(!isTop)
          }
        },
        { type: 'separator' },
        { label: 'Toggle Fullscreen', accelerator: 'F11', role: 'togglefullscreen' }
      ]
    },
    {
      label: 'Tools',
      submenu: [
        {
          label: 'Open Data Folder',
          click: () => {
            const dataPath = path.join(__dirname, '..', 'data')
            shell.openPath(dataPath)
          }
        },
        {
          label: 'Open Brain Memory',
          click: () => {
            shell.openPath('brain')
          }
        },
        { type: 'separator' },
        {
          label: 'Clear All Memory',
          click: async () => {
            const { dialog } = require('electron')
            const result = await dialog.showMessageBox(mainWindow, {
              type: 'warning',
              buttons: ['Cancel', 'Clear'],
              defaultId: 1,
              title: 'Clear Memory?',
              message: 'This will clear all learned knowledge and context. Continue?'
            })
            if (result.response === 1) {
              mainWindow.webContents.send('clear-memory')
            }
          }
        }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'About J.A.R.V.I.S.',
          click: () => {
            const { dialog } = require('electron')
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'About J.A.R.V.I.S.',
              message: 'J.A.R.V.I.S. Excel Agent',
              detail: 'Version 1.0.0\n\nAn AI-powered assistant for managing Excel files and Google Sheets databases.\n\nPowered by Ollama (qwen3)'
            })
          }
        }
      ]
    }
  ]

  // Mac-specific menu
  if (process.platform === 'darwin') {
    menuTemplate.unshift({
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services', submenu: [] },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideothers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    })
  }

  const menu = Menu.buildFromTemplate(menuTemplate)
  Menu.setApplicationMenu(menu)
}

function startFlaskServer() {
  return new Promise((resolve, reject) => {
    const flaskCwd = path.resolve(__dirname, '..')
    flaskProcess = spawn('python', ['app.py'], {
      cwd: flaskCwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: process.platform === 'win32'
    })

    let outputBuffer = ''
    const timeout = setTimeout(() => {
      reject(new Error('Flask startup timeout'))
    }, 30000)

    flaskProcess.stdout.on('data', (data) => {
      const text = data.toString()
      outputBuffer += text
      console.log(`[Flask] ${text.trim()}`)

      if (text.includes('Running on http') || text.includes('WARNING: This is a development server')) {
        clearTimeout(timeout)
        resolve()
      }
    })

    flaskProcess.stderr.on('data', (data) => {
      console.error(`[Flask ERR] ${data.toString().trim()}`)
    })

    flaskProcess.on('error', (err) => {
      clearTimeout(timeout)
      reject(err)
    })

    flaskProcess.on('exit', (code) => {
      if (!isQuitting) {
        console.log(`Flask exited with code ${code}`)
        app.quit()
      }
    })
  })
}

async function quitApp() {
  isQuitting = true

  if (flaskProcess) {
    flaskProcess.kill('SIGTERM')
    setTimeout(() => {
      if (flaskProcess) flaskProcess.kill('SIGKILL')
    }, 5000)
  }

  app.quit()
}

// App lifecycle
app.whenReady().async () => {
  try {
    console.log('Starting J.A.R.V.I.S. system...')
    await startFlaskServer()
    console.log('Flask server ready. Launching UI...')
    createWindow()
  } catch (err) {
    console.error('Failed to start Flask:', err)
    const { dialog } = require('electron')
    dialog.showErrorBox('Startup Error', `Could not start Flask server:\n${err.message}\n\nMake sure Python is installed and app.py is valid.`)
    app.quit()
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') quitApp()
})

// IPC handlers
ipcMain.handle('get-app-version', () => app.getVersion())
ipcMain.handle('is-dev', () => isDev)
