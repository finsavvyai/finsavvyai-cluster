const { app, BrowserWindow, Menu, ipcMain, Tray, nativeImage } = require('electron');
const path = require('path');
const axios = require('axios');
const isDev = require('electron-is-dev');

let mainWindow;
let tray;
let API_BASE_URL = 'http://localhost:8000'; // Local cluster API

// API service class
class FinSavvyAIService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async healthCheck() {
    try {
      const response = await axios.get(`${this.baseURL}/health`);
      return response.data;
    } catch (error) {
      throw new Error(`Health check failed: ${error.message}`);
    }
  }

  async getModels() {
    try {
      const response = await axios.get(`${this.baseURL}/v1/models`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get models: ${error.message}`);
    }
  }

  async getClusterStatus() {
    try {
      const response = await axios.get(`${this.baseURL}/cluster/status`);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to get cluster status: ${error.message}`);
    }
  }

  async chatCompletion(messages, model = 'gpt-3.5-turbo') {
    try {
      const response = await axios.post(`${this.baseURL}/v1/chat/completions`, {
        model,
        messages,
        max_tokens: 1000,
        temperature: 0.7
      });
      return response.data;
    } catch (error) {
      throw new Error(`Chat completion failed: ${error.message}`);
    }
  }
}

const finsavvyService = new FinSavvyAIService();

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 400,
    height: 600,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    },
    resizable: true,
    alwaysOnTop: true,
    skipTaskbar: true,
    frame: false,
    show: false
  });

  mainWindow.loadURL(
    isDev
      ? 'http://localhost:3000'
      : `file://${path.join(__dirname, '../build/index.html')}`
  );

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Hide to tray when closing
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
}

function createTray() {
  // Create tray icon (you'll need to add an icon file)
  const iconPath = path.join(__dirname, 'icon.png');
  tray = new Tray(iconPath);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Show FinSavvyAI',
      click: () => {
        mainWindow.show();
      }
    },
    { type: 'separator' },
    {
      label: 'Cluster Status',
      click: async () => {
        try {
          const status = await finsavvyService.getClusterStatus();
          console.log('Cluster Status:', status);
        } catch (error) {
          console.error('Failed to get cluster status:', error.message);
        }
      }
    },
    {
      label: 'Health Check',
      click: async () => {
        try {
          const health = await finsavvyService.healthCheck();
          console.log('Health:', health);
        } catch (error) {
          console.error('Health check failed:', error.message);
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Quit',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setToolTip('FinSavvyAI - Your Personal AI Assistant');
  tray.setContextMenu(contextMenu);

  tray.on('click', () => {
    mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
  });
}

function createMenu() {
  const template = [
    {
      label: 'FinSavvyAI',
      submenu: [
        {
          label: 'About FinSavvyAI',
          role: 'about'
        },
        { type: 'separator' },
        {
          label: 'Preferences',
          accelerator: 'CmdOrCtrl+,',
          click: () => {
            mainWindow.webContents.send('open-preferences');
          }
        },
        { type: 'separator' },
        {
          label: 'Quit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.quit();
          }
        }
      ]
    },
    {
      label: 'Cluster',
      submenu: [
        {
          label: 'Start Local Server',
          click: () => {
            mainWindow.webContents.send('start-server');
          }
        },
        {
          label: 'Stop Local Server',
          click: () => {
            mainWindow.webContents.send('stop-server');
          }
        },
        { type: 'separator' },
        {
          label: 'Add Worker',
          click: () => {
            mainWindow.webContents.send('add-worker');
          }
        }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { label: 'Undo', accelerator: 'CmdOrCtrl+Z', role: 'undo' },
        { label: 'Redo', accelerator: 'Shift+CmdOrCtrl+Z', role: 'redo' },
        { type: 'separator' },
        { label: 'Cut', accelerator: 'CmdOrCtrl+X', role: 'cut' },
        { label: 'Copy', accelerator: 'CmdOrCtrl+C', role: 'copy' },
        { label: 'Paste', accelerator: 'CmdOrCtrl+V', role: 'paste' }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// IPC handlers
ipcMain.handle('get-cluster-status', async () => {
  try {
    return await finsavvyService.getClusterStatus();
  } catch (error) {
    return { error: error.message };
  }
});

ipcMain.handle('get-health', async () => {
  try {
    return await finsavvyService.healthCheck();
  } catch (error) {
    return { error: error.message };
  }
});

ipcMain.handle('get-models', async () => {
  try {
    return await finsavvyService.getModels();
  } catch (error) {
    return { error: error.message };
  }
});

ipcMain.handle('chat-completion', async (event, messages, model) => {
  try {
    return await finsavvyService.chatCompletion(messages, model);
  } catch (error) {
    return { error: error.message };
  }
});

ipcMain.handle('set-api-url', (event, url) => {
  API_BASE_URL = url;
  finsavvyService.baseURL = url;
});

app.whenReady().then(() => {
  createWindow();
  createTray();
  createMenu();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
});

// Auto-updater (optional)
if (!isDev) {
  const { autoUpdater } = require('electron-updater');

  app.on('ready', () => {
    autoUpdater.checkForUpdatesAndNotify();
  });

  autoUpdater.on('update-available', () => {
    console.log('Update available');
  });

  autoUpdater.on('update-downloaded', () => {
    console.log('Update downloaded');
    autoUpdater.quitAndInstall();
  });
}
