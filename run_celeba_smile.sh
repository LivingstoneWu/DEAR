python train.py --data_dir /exports/eddie/scratch/ywu5/CelebA_Dataset/ \
                --dataloader_workers 8 \
                --labels age \
                --dec_dist implicit \
                --d_steps_per_iter 1 \
                --sample_every_epoch 5 \
                --latent_dim 100 \
                --enc_arch resnet \
                --save_model_every 5 \
                --n_epochs 200 \
                --prior linscm \
                --sup_prop 1 \
                --sup_coef 5 \
                --sup_type ce