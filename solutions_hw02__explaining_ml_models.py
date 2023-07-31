# -*- coding: utf-8 -*-
"""SOLUTIONS - HW02_ Explaining ML Models.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1uTuXFta5wVxUIsW9qLzmvEktiSn_u4U9

# Welcome to Homework #2: Explaining ML Models!
In this homework assignment you will complete the following three tasks
1. Implement 2 common saliency methods from scratch in pytorch
2. Use the python `lime` package to obtain LIME explanations
3. Use these explanation methods to explain the decision of two classifiers from HW1


##IMPORTANT:
  > Before you get started, select `Runtime > Change runtime type` and select `GPU` for your hardware accelerator.


##A couple of notes
1. Make sure to run each cell in order!
2. Only fill in code in sections marked as follows:
```
# <<<<<< Put your code here
# Write your code
# >>>>>
```

Let's get started!

## Environment Setup

First we have to install the `wilds` and `lime` python packages which will give us access to the Waterbirds dataset and an implementation of LIME. Run the command and give it ~1-3 min to install.
"""

# Commented out IPython magic to ensure Python compatibility.
# %%capture
# !pip install wilds
# !pip install lime

"""Now we load each of the packages we need for the worksheet. See the comments for the purpose of each"""

from wilds import get_dataset # Function to download wilds datasets
import torch # Pytorch library used for defining and training ML models
import torchvision # Package with utilities for computer vision such as pretrained models
import torchvision.transforms as transforms # Set of image transforms for processing image inputs
from lime import lime_image # Implmentation of LIME
from skimage.segmentation import mark_boundaries # Utility to show boundaries on an image
from lime.wrappers.scikit_image import SegmentationAlgorithm #Utility for segmenting boundaries
import numpy as np # Numpy used for general array manipulation
import matplotlib.pyplot as plt # Used for showing images
import os # Used to check the existence of files that we download
import warnings # Give warnings, such as if CUDA is unavailable

"""Now we check that GPU-support is available. If not, you may have forgotten to select the GPU hardware accelerator. We also set some useful constants."""

if not torch.cuda.is_available():
    warnings.warn(
        "CUDA is not available, please check that you have selected a GPU for hardware acceleration"
    )

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

"""## Download the dataset and the models

Run the command below to download the waterbirds dataset (should take 1-5 minutes to download). If your session stays active you won't need to re-download this each time you run it.
"""

dataset = get_dataset(dataset="globalwheat", download=True)

# Define the set of transforms used in the original paper

# These are the transforms that crop and resize the image
image_transform = transforms.Compose(
    [
        transforms.Resize((256, 256)),
        transforms.CenterCrop((224,224)),
    ]
)

# These are the transformas that convert the image to a tensor and normalize
tensor_transform = transforms.Compose(
    [
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225],),
    ]
)

pip install -U wilds

"""Again, lets visualize one training example from each subgroup"""

# Get the number of groups (should be 4)
n_groups = dataset._eval_grouper.n_groups

# Get a list of all the group ids for each data point in the dataset
group_ids = dataset._eval_grouper.metadata_to_group(dataset.metadata_array)

# Define the group and class labels
group_labels = ["Landbird on Land", "Landbird on Water", "Waterbird on Land", "Waterbird on Water"]
class_labels = ["Landbird", "Waterbird"]

# Sample one random image from each group
np.random.seed(2)
indices = [np.random.choice(np.where(group_ids == i)[0]) for i in range(n_groups)]
sample_images = [dataset[i][0] for i in indices]
labels = [dataset[i][1] for i in indices]

# Plot the figures with the group label as the title
fig, axs = plt.subplots(1, n_groups, figsize=(3*n_groups, 3))

for i in range(n_groups):
    axs[i].imshow(sample_images[i], extent=[0,1,0,1])
    axs[i].set_title(group_labels[i])
    axs[i].axis('off')

plt.subplots_adjust(wspace=0.2)
plt.show()

"""We are going to try to explain the predictions of the two models trained in HW #1: one trained using Empirical Risk Minimization (ERM) and one trained using Distributionally Robust Optimization over groups (GroupDRO). Download the two checkpoints from HW #1 for further analysis with explanations"""

!gdown https://drive.google.com/uc?id=17EN-zv_03x5_2nf6eFwlbgeFCpCukiSU
!gdown https://drive.google.com/uc?id=1N5IyGQx0KBYCVgPanymz-HmoSHyUUSA6

# Check for successful download
print()
if os.path.isfile('GroupDRO_resnet.ckpt') and os.path.isfile('ERM_resnet.ckpt'):
  print('Download successful!')
else:
  print('Error downloading data.')

"""Load the checkpoints in as PyTorch models. We will explain predictions from each of these models"""

ERM_resnet = torch.load("ERM_resnet.ckpt", map_location=DEVICE)
GroupDRO_resnet = torch.load("GroupDRO_resnet.ckpt", map_location=DEVICE)

"""## Saliency-based Explainability

### SmoothGrad
Define the saliency-based explainability technique of "smoothed gradients". Follow the instructions in the comments to implement this technique.
"""

# Function to compute smoothed gradients
# This function will take in a pytorch model and an image (represented in PIL format) and returns the SmoothGrad Explanation
# The hyperparameter sigma controls the standard deviation of the noise applied to the input to compute the smoothed gradient
# The hyperparameter n_samples controls the number of samples to generate and average over to compute the smoothed graident
def compute_smooth_gradients(model, image, sigma=0.10, n_samples=25):
    # Create an input batch
    input_tensor = tensor_transform(image_transform(image))
    input_tensor = input_tensor.unsqueeze(0).to(DEVICE)

    # Put the model into evaluation mode to disable anything like dropout or batchnorm updating
    model.eval()

    # Create a list that we will populate with the gradients
    gradients_list = []

    for _ in range(n_samples):
        # <<<<<< Put your code here

       # Create a noise tensor with the same size as the input_tensor [1 line]
        noise = torch.randn_like(input_tensor) * sigma

        # Add noise to the input_tensor [1 line]
        noisy_input = input_tensor + noise

        # Require gradients for this input [1 line]
        noisy_input.requires_grad = True

        # Forward pass with the noisy input [1 line]
        output = model(noisy_input)

        # Get the index corresponding to the predicted class [1 line]
        predicted_idx = torch.argmax(output)

        # Zero the model gradients [1 line]
        model.zero_grad()

        # Calculate gradients of the predicted output label  [1 line]
        output[0, predicted_idx].backward()

        # Extract the gradient with respect to the noisy input and append to the list of gradients [1-2 lines]
        # HINT: Make sure to use .clone().squeeze() to make a copy of the gradients and remove singular dimensions, respectively.
        # HINT: Make sure to append to the list "gradients_list" so the average can be computed
        gradients = noisy_input.grad.clone().squeeze()
        gradients_list.append(gradients)
        # >>>>>

    # Calculate the mean of the gradients
    mean_gradients = torch.mean(torch.stack(gradients_list), dim=0).detach().cpu()

    # Abs val max over channels for each pixel
    gradients = mean_gradients.abs().max(dim=0)[0]

    return gradients.numpy()

"""Now test the function to see if it works. The following code should run and produce a heatmap that represents the smoothed-gradient saliency of each pixel

"""

# Pull out the first image in the dataset
image = dataset[1][0]

# Compute the smooth-grad explanation
smooth_grads = compute_smooth_gradients(ERM_resnet, image)

# Plot the results
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
axes[0].imshow(transforms.Resize((256, 256))(image))
axes[0].set_title('Input Image')
axes[1].imshow(smooth_grads, cmap='hot')
axes[1].set_title('Smoothed Gradients')
plt.show()

"""What does the model seem to be paying attention to? What happens if you change the model to `GroupDRO_resnet`?

### Integrated Gradients
Now we will define the integrated gradients approach where we average the gradients over a series a points that interpolate from a black image to the target image. Follow the instructions in the comments to implement this technique.
"""

# Function to compute integrated gradients
# This function will take in a pytorch model and an image (represented in PIL format) and returns the Integrated gradients Explanation
# The hyperparameter n_steps controls the number of points to generate between the baseline and the input image.
def integrated_gradients(model, image, n_steps=25):
    # Create an input batch
    input_tensor = tensor_transform(image_transform(image))
    input_tensor = input_tensor.unsqueeze(0).to(DEVICE)
    input_tensor.requires_grad = True

    # Put the model into evaluation mode to disable anything like dropout or batchnorm updating
    model.eval()

    # Create a baseline image (in this case all black)
    baseline = torch.zeros_like(input_tensor).to(DEVICE)

    # <<<<<< Put your code here
    # Create a set of intermediate steps between the input image and baseline
    # NOTE: Call it step_sizes so we iterate over it in the for loop
    step_sizes = torch.linspace(0, 1, n_steps)[1:]
    # >>>>>

    # Create a list that we will populate with the gradients
    gradients_list = []

    # Loop over each step in the line
    for alpha in step_sizes:
        # <<<<<< Put your code here
        # Create an input that combines the baseline to the input_tensor using the step alpha [1 line]
        interpolated_input = baseline + alpha * (input_tensor - baseline)

        # Forward pass with the interpolated input [1 line]
        output = model(interpolated_input)

        # Get the index corresponding to the predicted class [1 line]
        predicted_idx = torch.argmax(output)

        # Zero the model gradients [1 line]
        model.zero_grad()

        # Calculate gradients of the predicted output label [1 line]
        output[0, predicted_idx].backward()

        # Extract the gradient with respect to the input_tensor and append to the list [1-2 lines]
        # HINT: Make sure to use .clone().squeeze() to make a copy of the gradients and remove singular dimensions, respectively.
        # HINT: Make sure to append to the list "gradients_list" so the average can be computed
        gradients = input_tensor.grad.clone().squeeze()
        gradients_list.append(gradients)
        # >>>>>

    # Calculate the mean of the gradients
    mean_gradients = torch.mean(torch.stack(gradients_list), dim=0)

    # Multiply by input image delta
    gradients = (input_tensor - baseline).squeeze()*mean_gradients
    gradients = gradients.detach().cpu()

    # Abs val max over channels for each pixel
    gradients = gradients.abs().max(dim=0)[0]

    return gradients.numpy()

"""Now test the function to see if it works. The following code should run and produce a heatmap that represents the integrated-gradient saliency of each pixel"""

# Pull out the first image in the dataset
image = dataset[1][0]

# Compute the integrated gradients explanation
integrated_grads = integrated_gradients(ERM_resnet, image)

# Plot the explanation
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
axes[0].imshow(transforms.Resize((256, 256))(image))
axes[0].set_title('Input Image')
axes[1].imshow(integrated_grads, cmap='hot')
axes[1].set_title('Integrated Gradients')
plt.show()

"""What does the model seem to be paying attention to? What happens if you change the model to `GroupDRO_resnet`?

## Locally Interpretable Model-agnostic Explanations (LIME)


---

In this section, we will use the package created by the original LIME author, which can be found [here](https://github.com/marcotcr/lime) (and which was already installed in the first cell of this notebook).

We will define a wrapper function that produces the LIME explanation for the model and image that are passed in.
"""

# Function to compute integrated gradients
# This function will take in a pytorch model and an image (represented in PIL format) and returns the LIME Explanation
# The hyperparameter num_samples controls the number of perturbed images used to build the LIME explanation
def LIME(model, image, num_samples=100):

    # This function is necessary to process a batch of images that have been perturbed.
    def batch_predict(images):
        model.eval()
        batch = torch.stack(tuple(tensor_transform(i) for i in images), dim=0).to(DEVICE)
        probs = torch.nn.functional.softmax(model(batch), dim=1)
        return probs.detach().cpu().numpy()

    # Generate a LIME explanation [~2 lines]
    # HINT: Look at cells 13 and 14 from the notebook example here: https://marcotcr.github.io/lime/tutorials/Tutorial%20-%20images.html
    # HINT: Make sure to apply the image_transformation to the input image as well as convert it to a np.array
    # <<<<<< Put your code here
    explainer = lime_image.LimeImageExplainer()
    explanation = explainer.explain_instance(np.array(image_transform(image)), batch_predict, num_samples=num_samples)
    # >>>>>

    return explanation

"""Test out our function to produce an explanation using LIME"""

# Pull out the first image in the dataset
image = dataset[1][0]

# Compute the LIME explanation
explanation = LIME(ERM_resnet, image)

# Extract the image mask show plot the results
temp, mask = explanation.get_image_and_mask(explanation.top_labels[0], positive_only=True, num_features=5, hide_rest=False)
img_boundry1 = mark_boundaries(temp/255.0, mask)
plt.imshow(img_boundry1)

"""## Comparison of Approaches


---

Now we will make comparisons of the different explanation techniques on a variety of images where our two models disagree.

Run the code below to generate all three types of explanations for our two different models: ERM and GroupDRO. We've pre-determined a number of images (one from each subgroup) where the two models disagree (see the commented out information for what each image is). Try generating explanations for the different images and see what the differences are.
"""

# image = dataset[690][0] # Group 0 (Landbird on Land) - ERM correctly predicts Landbird, GroupDRO incorrectly predicts Waterbird
image = dataset[1032][0] # Group 1 (Landbird on Water) - ERM incorrectly predicts Waterbird, GroupDRO correctly predicts Landbird
# image = dataset[82][0] # Group 2 (Waterbird on land), ERM incorrectly predicts Landbird, GroupDRO correctly predicts Waterbird
# image = dataset[87][0] # Group 3 (Waterbird on Water), ERM incorrectly predicts Landbird, GroupDRO correctly predicts Waterbird

models = [ERM_resnet, GroupDRO_resnet]
model_names = ["ERM", "GroupDRO"]


# Plot the saliency maps
fig, axes = plt.subplots(len(models), 4, figsize=(20, 5 * len(models)))

# Iterate over the models
for i, model in enumerate(models):
    # Compute saliency maps for the current model
    smooth_grads = compute_smooth_gradients(model, image)
    integrated_grads = integrated_gradients(model, image)
    lime_explanation = LIME(model, image)

    # Get the model prediction
    input_tensor = tensor_transform(image_transform(image))
    input_batch = input_tensor.unsqueeze(0).to(DEVICE)
    output = model(input_batch)
    predicted_idx = torch.argmax(output)
    predicted_class = class_labels[predicted_idx]

    # First column: Ground Truth
    axes[i, 0].imshow(transforms.Resize((256, 256))(image))
    axes[i, 0].set_title(f'Ground Truth (Pred = {predicted_class})')
    axes[i, 0].set_ylabel(model_names[i], fontweight='bold')

    # Second column: Smoothed Gradients
    axes[i, 1].imshow(smooth_grads, cmap='hot')
    axes[i, 1].axis('off')
    axes[i, 1].set_title('Smoothed Gradients')

    # Third column: Integrated Gradients
    axes[i, 2].imshow(integrated_grads, cmap='hot')
    axes[i, 2].axis('off')
    axes[i, 2].set_title('Integrated Gradients')

    # Fourth column: LIME
    temp, mask = lime_explanation.get_image_and_mask(lime_explanation.top_labels[0], positive_only=True, num_features=5, hide_rest=False)
    img_boundry1 = mark_boundaries(temp/255.0, mask)
    axes[i, 3].imshow(img_boundry1, cmap='hot')
    axes[i, 3].axis('off')
    axes[i, 3].set_title('LIME')

plt.tight_layout()
plt.show()

"""## Conclusion and Bonus Activities


---


Congratulations on completing the assignment! You can stop here, or if you want to try out some additional concepts from lecture consider trying one of the following


1. Experiment with different images. Are all of the explanations very clear?
2. Experiment with the different hyperparameters of the methods (noise level and number of samples for smoothgrad, number of steps for integrated gradients, or number of samples for LIME). Do the explanations depend on these parameters?
3. For a global-ish explanation, implement class model visualization from

```
Simonyan, Karen, Andrea Vedaldi, and Andrew Zisserman. "Deep inside convolutional networks: Visualising image classification models and saliency maps." arXiv preprint arXiv:1312.6034 (2013).
```
"""