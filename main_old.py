import numpy as np
import matplotlib.pyplot as plt
from metrics import print_metrics
from cli import get_training_dataset, read_images, is_pca, show_metrics
from eigen import calculate_eigenvectors
from preprocessing import PreProcessing, PCAPreprocessing, KPCAPreprocessing
from sklearn.decomposition import PCA

from classifier import Classifier


def preprocess_dataset(pca_processing, preprocessing, dataset):
    ret_list = []
    for data_i in dataset:
        stnd_img = preprocessing.regular_preprocess(data_i)
        ret_list.append(pca_processing.apply_pca(stnd_img))

    return ret_list


def train_with_svm(dataset_train, labels_train, classifier, is_pca, names):
    preprocessing = PreProcessing(dataset_train, dataset_train.shape[1], dataset_train.shape[2], dataset_train.shape[3])
    # Over this matrix we need to calculate eigenvectorss
    if is_pca:
        C_matrix = np.matmul(preprocessing.training_set, preprocessing.training_set.T)
    else:
        C_matrix = KPCAPreprocessing.rbf_kernel_pca(preprocessing.training_set)

    # Uses QR method to get eigenvalues and eigenvectors
    eigenvalues, eigenvec = np.linalg.eig(C_matrix) #calculate_eigenvectors(C_matrix)
    total = np.sum(np.abs(eigenvalues))

    accumulated = 0
    i = 0
    while accumulated < 0.50:
        accumulated = accumulated + eigenvalues[i]/total
        i = i + 1
    print(f"In order to win {round(accumulated, 4)} variance ratio we will use {i} eigenvectors")
    print("Training...")

    # Grab the first i eigenvectors
    eigenvectors = eigenvec[:i]

    if is_pca:
        # Apply PCA transformation to training training_data
        pca_processing = PCAPreprocessing(preprocessing.training_set, preprocessing.avg_face, eigenvectors,
                                            dataset_train.shape[1], dataset_train.shape[2], dataset_train.shape[3], names, labels_train)
    else:
        # Apply KPCA transformation to training training_data
        pca_processing = KPCAPreprocessing(preprocessing.training_set, preprocessing.avg_face, eigenvectors,
                                            dataset_train.shape[1], dataset_train.shape[2], dataset_train.shape[3], names, labels_train, C_matrix)

    # Train classifier with default C and gamma values
    classifier.train_classifier(pca_processing.training_set, labels_train)

    classifier.save(preprocessing, pca_processing)
    return preprocessing, pca_processing


def test_with_svm(dataset_test, classifier, preprocessing, pca_processing, show_testing_metrics,
                  labels_test, labels_train, names_test, names):
    # Apply PCA transformation to testing training_data
    dataset_test_pca = preprocess_dataset(pca_processing, preprocessing, dataset_test)

    labels_test_mapped_to_labels_train = []

    testing_with_training_dataset = True
    for label in labels_test:
        try:
            label_mapped = list(names).index(names_test[label])
        except:
            # If name is not in training dataset, then label is not mapped
            label_mapped = label
            # We can assume that user is not testing the dataset
            testing_with_training_dataset = False
            show_testing_metrics = False
        labels_test_mapped_to_labels_train.append(label_mapped)

    print(f"Shape of test set {dataset_test_pca}")
    # Test classifier
    y_pred = classifier.predict(dataset_test_pca)
    # classifier.save(preprocessing, pca_processing)

    # dataset_test = np.array(dataset_test_pca)
    # for i in range(dataset_test.shape[0]):
    #     pca_processing.reconstruct_image(dataset_test[i], names_test[labels_test[i]], names[y_pred[i]])

    # To obtain metrics
    print_metrics(y_pred, names, labels_test, labels_test_mapped_to_labels_train, names_test,
                  testing_with_training_dataset, show_testing_metrics)

    return [names[int(y_pred[i])] for i in range(len(y_pred))]


if __name__ == '__main__':

    # Initializing CLI Interface and obtaining training dataset
    dataset_train, labels_train, names = get_training_dataset()
    should_end = True if dataset_train is None or labels_train is None else False

    # Applying PCA or KPCA
    is_pca = is_pca()
    should_end = True if is_pca is None else False

    # Showing metrics
    show_testing_metrics = show_metrics()
    should_end = True if show_metrics is None else False

    # Training classifier
    classifier = Classifier()
    preprocessing, pca_processing = None, None
    if not should_end:
        preprocessing, pca_processing = train_with_svm(dataset_train, labels_train, classifier, is_pca, names)
        print("Training done! Now you can try the face recognition (or write exit to exit)")

    # Testing classifier
    while not should_end:
        path = input("Enter path to images or path to image: ")
        if path.lower() == "exit":
            should_end = True
            continue
        images, labels_test, names_test = read_images(path)
        if images is None:
            continue
        if images.shape[0] == 0:
            print("There are no images to test.")
            continue
        test_with_svm(images, classifier, preprocessing, pca_processing, show_testing_metrics,
                      labels_test=labels_test, labels_train=labels_train, names_test=names_test, names=names)
