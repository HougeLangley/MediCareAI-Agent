import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import patientTheme from './theme';
import ChatPage from './components/ChatPage';

function App() {
  return (
    <ThemeProvider theme={patientTheme}>
      <CssBaseline />
      <ChatPage />
    </ThemeProvider>
  );
}

export default App;
