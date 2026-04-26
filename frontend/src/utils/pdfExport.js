import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

export const exportToPDF = async (elementId, filename = 'rapport-ucar.pdf') => {
  const element = document.getElementById(elementId);
  if (!element) return false;

  try {
    // We use the native browser print which produces much higher quality PDFs
    // and naturally avoids all html2canvas "oklch" color parsing errors.
    
    // Add a specific class to the body to hide elements we don't want to print (like sidebar)
    document.body.classList.add('printing-mode');
    
    // Briefly wait for any CSS transitions
    await new Promise(resolve => setTimeout(resolve, 300));
    
    // Set document title temporarily to influence the default PDF save name
    const originalTitle = document.title;
    document.title = filename.replace('.pdf', '');
    
    window.print();
    
    // Restore state
    document.title = originalTitle;
    document.body.classList.remove('printing-mode');
    
    return true;
  } catch (error) {
    console.error('Erreur lors de la génération du PDF:', error);
    document.body.classList.remove('printing-mode');
    return false;
  }
};
