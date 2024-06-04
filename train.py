import tensorflow as tf
# from utils import vis, load_batch#, load_data
from utils import load_complete_data, show_batch_images
from model import DCGAN, dist_train_step#, train_step
from tqdm import tqdm
import os
import shutil
import pickle
from glob import glob
from natsort import natsorted
import wandb
import numpy as np
import cv2
from lstm_kmean.model import TripleNet
import math
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.style as style
from keras.src.engine import keras_tensor
# from eval_utils import get_inception_score
tf.random.set_seed(45)	
np.random.seed(45)

# Define the class names
#class_names = ['Apple', 'Car', 'Dog', 'Gold', 'Mobile', 'Rose', 'Scooter', 'Tiger', 'Wallet', 'Watch']

# Initialize the dictionaries
clstoidx = {}
idxtocls = {}

# Populate clstoidx and idxtocls dictionaries
"""for idx, class_name in enumerate(class_names):
    clstoidx[class_name] = idx
    idxtocls[idx] = class_name
"""

# Print the contents of idxtocls dictionary
#print("Contents of idxtocls dictionary:")
#print(idxtocls)
 
#data_dir = '/home/ravi/akash/EEG2Image/data/images'
#image_paths = glob(os.path.join(data_dir, '*', '*.jpg'))


for idx, item in enumerate(natsorted(glob('data/images/train/*')), start=0):
	clsname = os.path.basename(item)
	clstoidx[clsname] = idx
	idxtocls[idx] = clsname

image_paths = natsorted(glob('data/images/train/*/*'))
imgdict = {}
"""for path in image_paths:
    class_name = os.path.basename(os.path.dirname(path))
    if class_name in imgdict:
        imgdict[class_name].append(path)
    else:
        imgdict[class_name] = [path]"""


"""for class_index, class_name in enumerate(class_names):
    imgdict[class_name] = []  # Initialize an empty list for each class name

# Now you can populate imgdict with image paths for each class name
# Assuming the images for each class are stored in a directory named after the class
for class_name in class_names:
    class_dir = os.path.join('/home/ravi/akash/EEG2Image/data/images', class_name)
    if os.path.isdir(class_dir):
        img_paths = glob(os.path.join(class_dir, '*.jpg'))  # Adjust the file extension as needed
        imgdict[class_name] = img_paths
    else:
        print(f"Warning: Directory not found for class {class_name}")"""


for path in image_paths:
	key = path.split(os.path.sep)[-2]
	if key in imgdict:
		imgdict[key].append(path)
	else:
		imgdict[key] = [path]
"""print("Contents of imgdict:")
for class_name, image_paths in imgdict.items():
    print(f"Class: {class_name}, Number of Images: {len(image_paths)}")

print("\nContents of idxtocls dictionary:")
for idx, class_name in idxtocls.items():
    print(f"Index: {idx}, Class Name: {class_name}")"""

"""import os
import numpy as np
from glob import glob

# Function to load class names from directory structure
def load_class_names(data_dir):
    class_names = sorted(os.listdir(data_dir))
    return class_names

# Function to verify class labeling and indices
def verify_class_labels(data_dir, Y):
    # Load class names from directory structure
    class_names = load_class_names(data_dir)
    
    # Extract class indices from Y
    class_indices = np.argmax(Y, axis=1)
    
    # Print class indices and corresponding class names
    print("Class Indices:\n", class_indices)
    print("Class Names:\n", class_names)
    
    # Verify class labeling
    for idx, class_idx in enumerate(class_indices):
        if class_idx >= len(class_names):
            print(f"Warning: Class index {class_idx} exceeds the number of classes.")
        else:
            print(f"Sample {idx}: Predicted class '{class_names[class_idx]}' (Index: {class_idx})")

# Example usage
data_dir = '/home/ravi/akash/EEG2Image/data/images'  # Update with the path to your dataset directory
Y = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]])  # Example labels (replace with actual Y values)
verify_class_labels(data_dir, Y)
print(np.argmax(Y))
print("Keys in imgdict:", imgdict.keys())"""

"""# After populating imgdict, you can verify its contents
print("Keys in imgdict:", imgdict.keys())
for class_name, image_paths in imgdict.items():
    print(f"Class: {class_name}")
    for image_path in image_paths:
        print(image_path)
        
print("Keys in imgdict:", imgdict.keys())"""

"""print("Contents of idxtocls dictionary:")
for idx, cls_name in idxtocls.items():
    print(f"Index: {idx}, Class Name: {cls_name}")"""


# wandb.init(project='DCGAN_DiffAug_EDDisc_imagenet_128', entity="prajwal_15")
os.environ['TF_XLA_FLAGS'] = '--tf_xla_enable_xla_devices'
os.environ["CUDA_DEVICE_ORDER"]= "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]= '1'

if __name__ == '__main__':

	n_channels  = 14
	n_feat      = 128
	batch_size  = 128
	test_batch_size  = 1
	n_classes   = 10

	# data_cls = natsorted(glob('data/thoughtviz_eeg_data/*'))
	# cls2idx  = {key.split(os.path.sep)[-1]:idx for idx, key in enumerate(data_cls, start=0)}
	# idx2cls  = {value:key for key, value in cls2idx.items()}

	with open('/home/ravi/akash/EEG2Image/data/data.pkl', 'rb') as file:
		data = pickle.load(file, encoding='latin1')
		train_X = data['x_train']
		train_Y = data['y_train']
		test_X = data['x_test']
		test_Y = data['y_test']

	train_path = []
	for X, Y in zip(train_X, train_Y):
		train_path.append(np.random.choice(imgdict[idxtocls[np.argmax(Y)]], size=(1,) ,replace=True)[0])

	test_path = []
	for X, Y in zip(test_X, test_Y):
		test_path.append(np.random.choice(imgdict[idxtocls[np.argmax(Y)]], size=(1,) ,replace=True)[0])

	train_batch = load_complete_data(train_X, train_Y, train_path, batch_size=batch_size)
	test_batch  = load_complete_data(test_X, test_Y, test_path, batch_size=test_batch_size)
	X, Y, I      = next(iter(train_batch))
	latent_label = Y[:16]
	print(X.shape, Y.shape, I.shape)

	gpus = tf.config.list_physical_devices('GPU')
	mirrored_strategy = tf.distribute.MirroredStrategy(devices=['/GPU:1'], 
		cross_device_ops=tf.distribute.HierarchicalCopyAllReduce())
	n_gpus = mirrored_strategy.num_replicas_in_sync
	# print(n_gpus)

	# batch_size = 64
	latent_dim = 128
	input_res  = 128

	# print(latent_Y)
	# latent_Y = latent_Y[:16]
	# print

	triplenet = TripleNet(n_classes=n_classes)
	opt     = tf.keras.optimizers.legacy.Adam(learning_rate=3e-4)
	triplenet_ckpt    = tf.train.Checkpoint(step=tf.Variable(1), model=triplenet, optimizer=opt)
	triplenet_ckptman = tf.train.CheckpointManager(triplenet_ckpt, directory='lstm_kmean/experiments/best_ckpt', max_to_keep=5000)
	triplenet_ckpt.restore(triplenet_ckptman.latest_checkpoint)
	print('TripletNet restored from the latest checkpoint: {}'.format(triplenet_ckpt.step.numpy()))
	_, latent_Y = triplenet(X, training=False)

	print('Extracting test eeg features:')
	# test_eeg_features = np.array([np.squeeze(triplenet(E, training=False)[1].numpy()) for E, Y, X in tqdm(test_batch)])
	# test_eeg_y        = np.array([Y.numpy()[0] for E, Y, X in tqdm(test_batch)])
	test_image_count = 50000 #// n_classes
	# test_labels = np.tile(np.expand_dims(np.arange(0, 10), axis=-1), [1, test_image_count//n_classes])
	# test_labels = np.sort(test_labels.ravel())
	
	test_eeg_cls      = {}
	for E, Y, X in tqdm(test_batch):
		Y = Y.numpy()[0]
		if Y not in test_eeg_cls:
			test_eeg_cls[Y] = [np.squeeze(triplenet(E, training=False)[1].numpy())]
		else:
			test_eeg_cls[Y].append(np.squeeze(triplenet(E, training=False)[1].numpy()))
	
	for _ in range(n_classes):
		test_eeg_cls[_] = np.array(test_eeg_cls[_])
		print(test_eeg_cls[_].shape)

	for cl in range(n_classes):
		N = test_eeg_cls[cl].shape[0]
		per_cls_image = int(math.ceil((test_image_count//n_classes) / N))
		test_eeg_cls[cl] = np.expand_dims(test_eeg_cls[cl], axis=1)
		test_eeg_cls[cl] = np.tile(test_eeg_cls[cl], [1, per_cls_image, 1])
		test_eeg_cls[cl] = np.reshape(test_eeg_cls[cl], [-1, latent_dim])
		print(test_eeg_cls[cl].shape)

	# test_image_count = test_image_count // n_classes
	# print(test_eeg_features.shape, test_eeg_y.shape)

	lr = 3e-4
	with mirrored_strategy.scope():
		model        = DCGAN()
		model_gopt   = tf.keras.optimizers.Adam(learning_rate=lr, beta_1=0.2, beta_2=0.5)
		model_copt   = tf.keras.optimizers.Adam(learning_rate=lr, beta_1=0.2, beta_2=0.5)
		ckpt         = tf.train.Checkpoint(step=tf.Variable(1), model=model, gopt=model_gopt, copt=model_copt)
		ckpt_manager = tf.train.CheckpointManager(ckpt, directory='experiments/ckpt', max_to_keep=300)
		ckpt.restore(ckpt_manager.latest_checkpoint).expect_partial()

	# print(ckpt.step.numpy())
	START         = int(ckpt.step.numpy()) // len(train_batch) + 1
	EPOCHS        = 300#670#66
	model_freq    = 355#178#355#178#200#40
	t_visfreq     = 355#178#355#178#200#1500#40
	latent        = tf.random.uniform(shape=(16, latent_dim), minval=-0.2, maxval=0.2)
	latent        = tf.concat([latent, latent_Y[:16]], axis=-1)
	print(latent_Y.shape, latent.shape)
	
	if ckpt_manager.latest_checkpoint:
		print('Restored from last checkpoint epoch: {0}'.format(START))

	if not os.path.isdir('experiments/results'):
		os.makedirs('experiments/results')

	for epoch in range(START, EPOCHS):
		t_gloss = tf.keras.metrics.Mean()
		t_closs = tf.keras.metrics.Mean()

		tq = tqdm(train_batch)
		for idx, (E, Y, X) in enumerate(tq, start=1):
			batch_size   = X.shape[0]
			_, C = triplenet(E, training=False)
			gloss, closs = dist_train_step(mirrored_strategy, model, model_gopt, model_copt, X, C, latent_dim, batch_size)
			gloss = tf.reduce_mean(gloss)
			closs = tf.reduce_mean(closs)
			t_gloss.update_state(gloss)
			t_closs.update_state(closs)
			ckpt.step.assign_add(1)
			if (idx%model_freq)==0:
				ckpt_manager.save()
			if (idx%t_visfreq)==0:
				# latent_c = tf.concat([latent, C[:16]], axis=-1)
				X = mirrored_strategy.run(model.gen, args=(latent,))
				# X = X.values[0]
				print(X.shape, latent_label.shape)
				show_batch_images(X, save_path='experiments/results/{}.png'.format(int(ckpt.step.numpy())), Y=latent_label)

			tq.set_description('E: {}, gl: {:0.3f}, cl: {:0.3f}'.format(epoch, t_gloss.result(), t_closs.result()))
			# break

		with open('experiments/log.txt', 'a') as file:
			file.write('Epoch: {0}\tT_gloss: {1}\tT_closs: {2}\n'.format(epoch, t_gloss.result(), t_closs.result()))
		print('Epoch: {0}\tT_gloss: {1}\tT_closs: {2}'.format(epoch, t_gloss.result(), t_closs.result()))


		if (epoch%10)==0:
			save_path = 'experiments/inception/{}'.format(epoch)

			if not os.path.isdir(save_path):
				os.makedirs(save_path)

			for cl in range(n_classes):
				test_noise  = np.random.uniform(size=(test_eeg_cls[cl].shape[0],128), low=-1, high=1)
				noise_lst   = np.concatenate([test_noise, test_eeg_cls[cl]], axis=-1)

				for idx, noise in enumerate(tqdm(noise_lst)):
					X = mirrored_strategy.run(model.gen, args=(tf.expand_dims(noise, axis=0),))
					X = cv2.cvtColor(tf.squeeze(X).numpy(), cv2.COLOR_RGB2BGR)
					X = np.uint8(np.clip((X*0.5 + 0.5)*255.0, 0, 255))
					cv2.imwrite(save_path+'/{}_{}.jpg'.format(cl, idx), X)

			# eeg_feature_vectors_test = np.array([test_eeg_features[np.random.choice(np.where(test_eeg_y == test_label)[0], size=(1,))[0]] for test_label in test_labels])
			# latent_var  = np.concatenate([test_noise, eeg_feature_vectors_test], axis=-1)
			# print(test_noise.shape, eeg_feature_vectors_test.shape, latent_var.shape)
			# for idx, noise in enumerate(tqdm(latent_var)):
			# 	X = mirrored_strategy.run(model.gen, args=(tf.expand_dims(noise, axis=0),))
			# 	X = cv2.cvtColor(tf.squeeze(X).numpy(), cv2.COLOR_RGB2BGR)
			# 	X = np.uint8(np.clip((X*0.5 + 0.5)*255.0, 0, 255))
			# 	cv2.imwrite(save_path+'/{}_{}.jpg'.format(test_labels[idx], idx), X)
			# print(X.shape)
		# break 
