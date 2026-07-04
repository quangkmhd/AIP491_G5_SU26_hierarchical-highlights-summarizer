#!/usr/bin/env python3
import os
from pathlib import Path
from dotenv import load_dotenv
from datalab_sdk import DatalabClient, ConvertOptions

def main():
    # Load .env file
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
    
    # Retrieve the API key and clean it up (in case of leading/trailing whitespace/quotes)
    api_key = os.getenv("DATALAB_API_KEY_2")
    if not api_key:
        print("Error: DATALAB_API_KEY_2 not found in environmental variables or .env file.")
        return
    
    api_key = api_key.strip().strip("'\"")
    
    # Define files to convert
    current_dir = Path(__file__).parent
    pdf_files = [
        current_dir / "2021.sigdial-1.18.pdf",
        current_dir / "2307.15793v3.pdf"
    ]
    
    # Initialize Datalab client
    print("Initializing DatalabClient...")
    client = DatalabClient(api_key=api_key, timeout=300)
    
    for pdf_path in pdf_files:
        if not pdf_path.exists():
            print(f"Error: File not found at {pdf_path}")
            continue
            
        md_path = pdf_path.with_suffix(".md")
        print(f"\nConverting {pdf_path.name} -> {md_path.name}...")
        
        try:
            # Execute conversion
            result = client.convert(
                file_path=str(pdf_path),
                options=ConvertOptions(
                    output_format="markdown",
                    mode="accurate"
                ),
                save_output=str(md_path)
            )
            
            if result.success:
                print(f"Success! Saved markdown to {md_path.name}")
                if hasattr(result, "page_count"):
                    print(f"Total pages processed: {result.page_count}")
            else:
                error_msg = getattr(result, "error", "Unknown error during conversion.")
                print(f"Failed to convert {pdf_path.name}: {error_msg}")
                
        except Exception as e:
            print(f"Exception raised while converting {pdf_path.name}: {e}")

if __name__ == "__main__":
    main()
