import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader
import os
import time

def train_model():
    # 1. Setup Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on device: {device}")

    # 2. Data Preparation
    data_dir = "training_data/scalping"
    
    # Define transforms
    data_transforms = {
        'train': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomRotation(10),
            transforms.ColorJitter(brightness=0.2, contrast=0.2),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
        'val': transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ]),
    }

    # Load dataset
    full_dataset = datasets.ImageFolder(data_dir, transform=data_transforms['train'])
    
    # Handle imbalanced classes with WeightedRandomSampler
    class_counts = [0] * len(full_dataset.classes)
    for _, index in full_dataset.samples:
        class_counts[index] += 1
    
    weights = [1.0 / count if count > 0 else 0 for count in class_counts]
    sample_weights = [weights[index] for _, index in full_dataset.samples]
    sampler = torch.utils.data.WeightedRandomSampler(sample_weights, len(sample_weights))

    train_loader = DataLoader(full_dataset, batch_size=8, sampler=sampler)
    
    print(f"Classes: {full_dataset.classes}")
    print(f"Class counts: {class_counts}")

    # 3. Model Architecture (ResNet18)
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    num_ftrs = model.fc.in_features
    # Adjust for number of classes in training_data/scalping/
    model.fc = nn.Linear(num_ftrs, len(full_dataset.classes))
    model = model.to(device)

    # 4. Training Parameters
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # 5. Training Loop
    num_epochs = 15
    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        running_corrects = 0
        
        for inputs, labels in train_loader:
            inputs = inputs.to(device)
            labels = labels.to(device)
            
            optimizer.zero_grad()
            
            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            loss = criterion(outputs, labels)
            
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)
            
        epoch_loss = running_loss / len(full_dataset)
        epoch_acc = running_corrects.double() / len(full_dataset)
        
        print(f'Epoch {epoch}/{num_epochs - 1} | Loss: {epoch_loss:.4f} Acc: {epoch_acc:.4f}')

    # 6. Save Model
    os.makedirs("data", exist_ok=True)
    save_path = "data/chart_classifier.pth"
    torch.save(model.state_dict(), save_path)
    print(f"Model saved to {save_path}")

if __name__ == "__main__":
    train_model()
