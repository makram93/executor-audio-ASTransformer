from collections import Iterable

from jina import Executor, DocumentArray, requests
from  ast_exec.ast_models import ASTModel
import ast_exec.ast_params as params
from ast_exec.ast_input import *

class ASTransformer_encoder(Executor):

    def __init__(self,
                 total_labels: int = 527,
                 input_target_dim: int = 1024,
                 dataset_mean_std: list =[-4.2677393, 4.5689974],
                 model_path: str = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_target_dim=input_target_dim
        self.total_labels=total_labels
        self.path = model_path
        self.model = self.get_model(model_path)
        self.mean= dataset_mean_std[0]
        self.std=dataset_mean_std[1]

    def get_model(self, path):
        """
        Lood the AST model in the memory
        :param path: path to the model
        :return: AST model
        """
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        audio_model = ASTModel(label_dim=self.total_labels, fstride=params.FSTRIDE, tstride=params.TSTRIDE, input_fdim=params.INPUT_FDIM,
                                      input_tdim=self.input_target_dim, imagenet_pretrain=params.IMAGENET_PRETRAIN,
                                      audioset_pretrain=params.AUDIOSET_PRETRAIN, model_size=params.MODEL_SIZE)
        if self.path:
            print(f'Model Path: {path}')
            sd = torch.load(path, map_location=device)
            audio_model = torch.nn.DataParallel(audio_model)
            audio_model.load_state_dict(sd)
        print(f'Model Path After: {path}')
        audio_model.eval()
        audio_model.to(device)
        print("model loaded")
        return audio_model


    @requests
    def encode(self, docs: DocumentArray, **kwargs):
        """
               Compute embeddings and store them in the `docs` array.

               :param docs: documents sent to the encoder. The docs must have `text`.
                   By default, the input tags of the document must contain a key 'filename' that should contain
                   the full name of the audio file.
               :param kwargs: Additional key value arguments.
               :return:
               """
        if docs:
            self._create_embeddings(docs)

    def _create_embeddings(self, filtered_docs: Iterable):
        """Update the documents with the embeddings generated by AST"""

        for d in filtered_docs:
            # Vggish broadcasts across different length audios, not batches
            input = get_input(d.tags['filename'], self.input_target_dim, self.mean, self.std)
            with torch.no_grad():
                pred, embedding = self.model(input)
            # output should be in shape [10, 50], i.e., 10 samples, each with prediction of 50 classes.
            sm = torch.nn.Softmax(dim=-1)
            pred=  pred.argmax()
            d.tags['prediction']= pred.tolist()
            d.embedding = embedding.numpy()