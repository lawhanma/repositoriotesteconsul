require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const API_KEY = process.env.ATHENAS_API_KEY;

if (!API_KEY) {
  console.error('ERRO: ATHENAS_API_KEY não definida no .env');
  process.exit(1);
}

app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Rota de saúde
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Servidor de consulta CPF online' });
});

// Endpoint principal de consulta
app.post('/api/consulta-cpf', async (req, res) => {
  const { cpf } = req.body;

  if (!cpf) {
    return res.status(400).json({ error: 'CPF é obrigatório' });
  }

  const cpfLimpo = String(cpf).replace(/\D/g, '');

  if (cpfLimpo.length !== 11) {
    return res.status(400).json({ error: 'CPF deve conter exatamente 11 dígitos' });
  }

  try {
    const response = await fetch(`https://api.athenasbuscas.com/api/ext/v1/cpf/${cpfLimpo}`, {
      method: 'GET',
      headers: {
        'X-API-Key': API_KEY,
        'Accept': 'application/json'
      }
    });

    const creditsRemaining = response.headers.get('X-Credits-Remaining');
    let data;

    try {
      data = await response.json();
    } catch {
      data = { error: 'Resposta inválida da API' };
    }

    if (!response.ok) {
      return res.status(response.status).json({
        success: false,
        error: data.error || data.message || `Erro HTTP ${response.status}`,
        status: response.status,
        creditsRemaining: creditsRemaining || null
      });
    }

    res.json({
      success: true,
      data,
      creditsRemaining: creditsRemaining || null
    });

  } catch (err) {
    console.error('Erro na consulta:', err.message);
    res.status(500).json({
      success: false,
      error: 'Erro interno ao consultar a API. Tente novamente.'
    });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`✅ Servidor rodando em http://localhost:${PORT}`);
  console.log(`🔑 API Key carregada: ${API_KEY.substring(0, 8)}...`);
});
