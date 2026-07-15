srun --jobid=9376732 --overlap --pty /bin/bash
cd /mnt/scratch2/users/mmohseni/projects/medsam3/medsam1
conda activate "$PWD/.venv"
streamlit run app.py
