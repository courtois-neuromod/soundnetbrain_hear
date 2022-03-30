import os
import numpy as np
from torch import load, device
import torch
from .model import SoundNetEncoding_conv


def load_model(model_file_path, device=None):
    if device is None:
        device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

    modeldict = load(model_file_path, map_location=device)

    model = SoundNetEncoding_conv(out_size=modeldict['out_size'],output_layer=modeldict['output_layer'],
    kernel_size=modeldict['kernel_size'])

    # Set model weights using checkpoint file
    model.load_state_dict(modeldict['checkpoint'])

    model.sample_rate = 22000  # Input sample rate
    model.scene_embedding_size = 1024
    model.timestamp_embedding_size = 128

    return model


def get_scene_embeddings(x, model):

    audio_length = x.shape[2]
    minimum_length = 32000

    if audio_length < minimum_length:
        batch_size = x.shape[0]
        device = x.device
        x = torch.cat((x, torch.zeros(batch_size, 1,minimum_length - audio_length,1).to(device)), dim=2)

    with torch.no_grad():
        model.eval()
        Y,outputlist = model.soundnet.extract_feat(x,'conv7')
    
    Y=Y[:,:,0]
    
    conv7 = torch.mean(Y,axis=2)
    return conv7


def get_timestamp_embeddings(x, model):
    audio_length = x.shape[2]
    minimum_length = 32000

    if audio_length < minimum_length:
        batch_size = x.shape[0]
        device = x.device
        x = torch.cat((x, torch.zeros(batch_size, 1,minimum_length - audio_length,1).to(device)), dim=2)

    with torch.no_grad():
        model.eval()
        Y,outputlist = model.soundnet.extract_feat(x,'conv4')
    
    embs=Y[:,:,:,0].swapaxes(1,2)

    batch_size, frames_num, embedding_size = embs.shape

    ### perio and offset were estimated using soundnet architecture, taking into account paddings, strides and maxpool
    offset = 0.08
    perio = 1 / 10.725
    time_steps = (torch.arange(frames_num-1)[None, :] * perio) + offset    # (frames_num,)
    time_steps = time_steps.repeat(batch_size, 1)   # (batch_size, frames_num)
    
    
    return embs[:,1:,:],time_steps