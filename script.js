const fs = require('fs');
const path = require('path');

// Função para transformar uma string de caminho em array
function transformPathToArray(pathString) {
    if (typeof pathString !== 'string' || !pathString.startsWith('/')) {
        return pathString; // Retorna o valor original se não for um caminho válido
    }
    
    // Remove a primeira barra e divide por '/'
    return pathString.substring(1).split('/');
}

// Função recursiva para processar objetos e arrays
function processObject(obj) {
    if (Array.isArray(obj)) {
        return obj.map(item => processObject(item));
    } else if (obj !== null && typeof obj === 'object') {
        const result = {};
        for (const [key, value] of Object.entries(obj)) {
            result[key] = processObject(value);
        }
        return result;
    } else if (typeof obj === 'string' && obj.startsWith('/')) {
        return transformPathToArray(obj);
    } else {
        return obj;
    }
}

// Função principal
function main() {
    try {
        // Lê o arquivo txt
        const filePath = path.join(__dirname, 'arquivo.txt');
        const fileContent = fs.readFileSync(filePath, 'utf8');
        
        // Parse do JSON
        const jsonData = JSON.parse(fileContent);
        
        // Processa o objeto transformando os caminhos em arrays
        const transformedData = processObject(jsonData);
        
        // Salva o resultado em um novo arquivo
        const outputPath = path.join(__dirname, 'arquivo_transformado.json');
        fs.writeFileSync(outputPath, JSON.stringify(transformedData, null, 2), 'utf8');
        
        console.log('✅ Transformação concluída!');
        console.log(`📄 Arquivo original: ${filePath}`);
        console.log(`📄 Arquivo transformado: ${outputPath}`);
        
        // Mostra um exemplo da transformação
        console.log('\n📋 Exemplo de transformação:');
        console.log('Antes:', '/NFe/infNFe/ide/natOp');
        console.log('Depois:', transformPathToArray('/NFe/infNFe/ide/natOp'));
        
    } catch (error) {
        console.error('❌ Erro ao processar o arquivo:', error.message);
    }
}

// Executa o script
main();