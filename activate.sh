# cd /mnt/scratch2/users/mmohseni/projects/medsam3/medsam3
# conda activate "$PWD/.venv"
# streamlit run app.py


# cd /mnt/scratch2/users/mmohseni/projects/medsam3/sam3
# conda activate "$PWD/.venv"
# streamlit run app.py


cd segmentation_labeler
uv sync --dev
npm --prefix frontend install
make run