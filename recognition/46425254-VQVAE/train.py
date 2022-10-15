import torch
import torch.nn as nn
import torch.utils as utils
import torchvision
import numpy as np

import modules
import dataset
import visualise as vis

import CNNcopy
import matplotlib.pyplot as plt
from skimage.metrics import structural_similarity as ssim



        
class VQ_Training():
    
    
    def __init__(self, learning_rate, epochs, train_path, test_path, 
                 save = None, visualise = False):
        super(VQ_Training).__init__()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.learning_rate = learning_rate
        self.epochs = epochs
        self.data = dataset.DataLoader(train_path)
        self.data2 = dataset.DataLoader(test_path)
        self.training_data = \
            utils.data.DataLoader(self.data, batch_size = 15, shuffle = True)
        
        self.testing_data = \
            utils.data.DataLoader(self.data, batch_size = 1, shuffle = True)
        
        self.model = modules.VQVAE().to(self.device)
        
        self.optimizer = \
            torch.optim.Adam(self.model.parameters(), lr = learning_rate)
        
        self.save = save
        self.visualise = visualise
        if self.visualise == True:
            self.visualiser = vis.Visualise(self.model, self.data)
            
    def train(self):
        epoch = 0
        loss = []
        while epoch != self.epochs:
            
            sub_step = 0
            for i, _ in self.training_data:
                i = i.view(-1, 3, 256, 256).to(self.device)
                
                decoder_outputs, VQ_loss = self.model(i)
                #reset the optimizer gradients to 0 to avoid resuing prev iteration's 
                self.optimizer.zero_grad()
                
                #calculate reconstruction loss
                recon_loss = nn.functional.mse_loss(decoder_outputs, i)
                
                #calculate total loss
                total_loss = recon_loss + VQ_loss
                
                #update the gradient 
                total_loss.backward()
                self.optimizer.step()
                
                if sub_step == 0:
                    print(
                        f"Epoch [{epoch}/{self.epochs}] \ " 
                        f"Loss : {total_loss:.4f}"
                    )
                    loss.append(total_loss.item())
                    
                    if self.visualise == True:
                        self.visualiser.VQVAE_discrete((0,0))
                        self.visualiser.visualise_VQVAE((0,0))
        
                
                
                sub_step += 1
            epoch += 1
        plt.plot(np.arange(0, self.epochs), loss)
        plt.show()
        
                    
        # save anyways if loop finishes by itself
        if self.save != None:
            
            torch.save(self.model.state_dict(), self.save)
    """
    Testing for VQVAE outputs
    
    If Visualise is selected, then it visulises the decoded outputs, 
    
    """
    def test(self):
        ssim_list = []
        max_ssim = 0
        for i, _ in self.testing_data:
            i = i.view(-1, 3, 256, 256).to(self.device).detach()
            real_grid = torchvision.utils.make_grid(i, normalize = True)
            decoded_img , _ = self.model(i)
            decoded_img = decoded_img.view(-1, 3, 256,256).to(self.device).detach()
            decoded_grid = \
                torchvision.utils.make_grid(decoded_img, normalize = True)
            decoded_grid = decoded_grid.to("cpu").permute(1,2,0)
            real_grid = real_grid.to("cpu").permute(1,2,0)
            val =\
                ssim(real_grid.numpy(), decoded_grid.numpy(), channel_axis = -1)
            if max_ssim < val:
                max_ssim = val
        ssim_list.append(val)
        print("The Average SSIM for the test data is " + (str) (np.average(ssim_list)))
        print("The maximum SSIM is " + (str) (np.amax(ssim_list)))
        
        
data_path = r"C:\Users\blobf\COMP3710\PatternFlow\recognition\46425254-VQVAE\keras_png_slices_data\train"
data_path2 = r"C:\Users\blobf\COMP3710\PatternFlow\recognition\46425254-VQVAE\keras_png_slices_data\test"

trained = r"C:\Users\blobf\COMP3710\PatternFlow\recognition\46425254-VQVAE\trained_model\bruh.pt"
#lr = 0.0002
#epochs  = 15

#trainer = VQ_Training(lr, epochs, data_path, data_path2, 
                    #  save = trained, visualise=True)
#trainer.train()
#trainer.test()
class PixelCNN_Training():
    
    def __init__(self, lr, epochs, model_path, data_path, save = None):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.lr = lr
        self.epochs = epochs
        self.model_path = model_path
        model = modules.VQVAE()
        model.load_state_dict(torch.load(model_path))
        model.eval()
        self.model = model
        self.epochs = epochs
        self.data = dataset.DataLoader(data_path)
        self.training_data = \
            utils.data.DataLoader(self.data, batch_size = 16, shuffle = True)
        
       # self.loss = nn.functional.cross_entropy()
        self.save = save
        
        self.PixelCNN_model = modules.PixelCNN().to(self.device)
        self.optimizer = \
            torch.optim.Adam(self.PixelCNN_model.parameters(), lr = lr)
            
    def train(self):
        epoch = 0
        training_loss_arr = []

        while epoch != self.epochs+1:
            
            sub_step = 0
            for i, _ in self.training_data:
                i = i.view(-1, 3, 256, 256)
                
                with torch.no_grad():
                    encoder = self.model.get_encoder().to(self.device)
                    VQ = self.model.get_VQ().to(self.device)
                    decoder = self.model.get_decoder().to(self.device)
                    i = i.to(self.device)
                    encoded = encoder(i)
                    encoded = encoded.permute(0, 2, 3, 1).contiguous()
                    flat_encoded  = encoded.reshape(-1, VQ.embedding_dim)
                    
                    a, b = VQ.argmin_indices(flat_encoded)
              
                    b = b.view(-1, 64, 64)
                    c = nn.functional.one_hot(b, num_classes = 128).float()
                    c = c.permute(0, 3, 1, 2)
                    #b = b.permute(1, 0, 2, 3).contiguous()
                prior = self.PixelCNN_model(c)
                self.optimizer.zero_grad()
       
                total_loss = nn.functional.cross_entropy(prior, b)
                
                total_loss.backward()
                self.optimizer.step()
                
                if sub_step == 0:
                    print(
                        f"Epoch [{epoch}/{self.epochs}] \ " 
                        f"Loss : {total_loss:.4f}"
                    )
                    
                    training_loss_arr.append(total_loss.item())
                    if self.save != None:
                        torch.save(self.PixelCNN_model.state_dict(), self.save)
                    gen_image(self.model_path, self.save)
                    
                    #if self.visualise == True:
                     #   self.visualiser.VQVAE_discrete((0,0))
                sub_step += 1
                
                
            epoch += 1
        #save if user interrupts
         
                    
        # save anyways if loop finishes by itself
        if self.save != None:
            
            torch.save(self.PixelCNN_model.state_dict(), self.save)

        plt.plot(np.arange(0, self.epochs), training_loss_arr)
        plt.show()
        
def gen_image(train_path, model_path):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = modules.VQVAE()
    state_dict = torch.load(train_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    
    cnn = modules.PixelCNN()
    state_dict = torch.load(model_path, map_location="cpu")
    cnn.load_state_dict(state_dict)
    cnn.to(device)
    cnn.eval()
 
    prior = torch.zeros((1, 128, 64, 64), device = device)
    
    _, channels, rows, cols = prior.shape
    
    
    with torch.no_grad():
        for i in range(rows):
            for j in range(cols):
                # argmax removes things that is not predicted
                out = cnn(prior.float())
                #print(out.shape)
                #.argmax(1)
                out = out.permute(0,2,3,1).contiguous()
                #probs = nn.functional.one_hot(out, num_classes = 128).permute(0, 3, 1, 2).contiguous()
                distribution = torch.distributions.categorical.Categorical(logits = out)
                sampled = distribution.sample()
                #print(sampled.shape)
                sampled = nn.functional.one_hot(sampled, num_classes = 128
                                                ).permute(0, 3, 1, 2).contiguous()
                #print(sampled.shape)
                prior[:, :, i , j] = sampled[:, :, i, j]
          
    #prior = prior.argmax(1)
    #prior = nn.functional.one_hot(prior, num_classes= 128)
    _, ax = plt.subplots(1,2)
    ax[0].imshow(prior.argmax(1).view(64,64).to("cpu"))
    ax[0].title.set_text("Latent Generation")
 #   prior = nn.functional.one_hot(prior, num_classes= 128)
 #   prior = prior.permute(0, 3, 1, 2).contiguous()
    prior = prior.view(1,128,-1)
    prior = prior.permute(0,2,1).float()
    quantized_bhwc = torch.matmul(prior, 
                                  model.get_VQ().embedding_table.weight)
    
    quantized_bhwc = quantized_bhwc.view(1, 64, 64 ,16)
    quantized = quantized_bhwc.permute(0, 3, 1, 2).contiguous()
    
    decoded = model.get_decoder()(quantized).to(device)
    
    decoded = decoded.view(-1, 3, 256,256).to(device).detach()
    
    decoded_grid = \
        torchvision.utils.make_grid(decoded, normalize = True)
    #print(decoded_grid.shape)
    decoded_grid = decoded_grid.to("cpu").permute(1,2,0)
    
    ax[1].imshow(decoded_grid)
    ax[1].title.set_text("Decoded Generation")
    plt.show()
        
save_model =  r"C:\Users\blobf\COMP3710\PatternFlow\recognition\46425254-VQVAE\trained_model\cnn_model.pt"
pixel_cnn_trainer = PixelCNN_Training(0.0005, 300, trained,data_path, save = save_model)
pixel_cnn_trainer.train()



 
