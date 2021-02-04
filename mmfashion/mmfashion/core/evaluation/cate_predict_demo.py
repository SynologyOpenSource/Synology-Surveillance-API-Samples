import numpy as np
import torch


class CatePredictor(object):

    def __init__(self, cfg, tops_type=[1, 3, 5]):
        """Create the empty array to count true positive(tp),
            true negative(tn), false positive(fp) and false negative(fn).

        Args:
            class_num : number of classes in the dataset
            tops_type : default calculate top3, top5 and top10
        """

        cate_cloth_file = open(cfg.cate_cloth_file).readlines()
        self.cate_idx2name = {}
        for i, line in enumerate(cate_cloth_file[2:]):
            self.cate_idx2name[i] = line.strip('\n').split()[0]

        self.tops_type = tops_type

    def print_cate_name(self, pred_idx):
        for idx in pred_idx:
            print(self.cate_idx2name[idx])

    def print_cate_conf(self, pred_idx, data):
        for idx in pred_idx:
            print(data[idx])

    def show_prediction(self, pred):
        if isinstance(pred, torch.Tensor):
            data = pred.data.cpu().numpy()
        elif isinstance(pred, np.ndarray):
            data = pred
        else:
            raise TypeError('type {} cannot be calculated.'.format(type(pred)))

        for i in range(pred.size(0)):
            indexes = np.argsort(data[i])[::-1]
            for topk in self.tops_type:
                idxes = indexes[:topk]
                print('[ Top%d Category Prediction ]'%topk)
                self.print_cate_name(idxes)
                self.print_cate_conf(idxes, data[i])

    def get_prediction_from_samples(self, pred, top_k):
        if isinstance(pred, torch.Tensor):
            data = pred.data.cpu().numpy()
        elif isinstance(pred, np.ndarray):
            data = pred
        else:
            raise TypeError('type {} cannot be calculated.'.format(type(pred)))

        results = []
        confidences = []

        for i in range(pred.size(0)):
            indexes = np.argsort(data[i])[::-1]
            idxes = indexes[:top_k]

            result = []
            confidence = []
            for idx in idxes:
                cate_name = self.cate_idx2name[idx]
                result.append(cate_name)

                conf = data[i][idx]
                confidence.append(conf)

            results.append(result)
            confidences.append(confidence)

        return results, confidences
