# Constructing a deprivation index following the AF methodology
# Created by Gregory Ho

import pandas as pd
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from factor_analyzer import FactorAnalyzer

### To run, the following parameters are instantiated ###

# 1) thresholds represent pre-defined cutoffs obtained from our literature review
thresholds = {
'violent_crime': 1114, #corresponding to 1st quantile
'non_offensive_crime':528.4, #corresponding to 1st quantile
'RTI_ratio': 0.3, # based on literature review
'time_to_CBD': 1200, # based on literature review
'distance_to_CBD': 7273.2 #corresponding to 1st quantile
}

# 2) specify fixed cutoff as specified in AF method. 
#    Criteria is to censor data for non-deprived neighborhoods
#    k=0 because we have low count of sub-indicators
k = 0

# 3) path to clean data
cleaned_data = "deprivation_evictions/data_bases/clean_data/clean_database.csv"
transport_data = "deprivation_evictions/data_bases/raw_data/google_distancematrix.csv"
output_path = "deprivation_evictions/data_bases/final_data/processed_data.csv"

# 4) PCA parameters (This segment is for further analysis, unutilized in our viz)
n_comp = 5
rotate_fn = "varimax"


class MultiDimensionalDeprivation:
    def __init__(self, k, cleaned_data, thresholds):
        '''
        constructor
        '''
        self.k = k
        self.data = pd.read_csv(cleaned_data)
        self.thresholds = thresholds
        self.indicators = list(thresholds.keys())

    def compute_ratios(self):
        '''
        This function takes in cleaned data and performs some row operations to 
        compute intermediate values
        Inputs:
        cleaned_data    : takes in cleaned data

        Returns:
        extended_data   : processed data in the form of a pandas dataframe
        '''
        cleaned_data = self.data
        travel_data = pd.read_csv(transport_data)
        travel_data = travel_data.groupby('zipcode')[['time_to_CBD', 'distance_to_CBD']].mean()

        # Compute intermediate values
        cleaned_data["RTI_ratio"] = cleaned_data["RentPrice"]/(cleaned_data["hh_median_income"]/12)
        # [KIV]
        cleaned_data = cleaned_data.rename(columns={'zip_code': 'zipcode'})
        merged_data = pd.merge(cleaned_data, travel_data, on='zipcode', how='inner')
        return merged_data

    def raw_normalized_viz(self):
        '''
        Normalizes dimensions (for vizualization: radial plot)

        Input: merged_data
        Returns: matrix Y in normalized form
        '''
        mat_y_norm = self.compute_ratios()

        for col in mat_y_norm.columns:
            if col in self.indicators:
                dim_means = mat_y_norm[col].mean()
                dim_stds = mat_y_norm[col].std()
                mat_y_norm[col] =  (mat_y_norm[col] - dim_means) / dim_stds

        #filter only columns that were standardized 
        mat_y_norm = mat_y_norm[[col for col in mat_y_norm.columns if col in self.indicators]]

        return mat_y_norm
        
    def deprivation_matrix(self):
        '''
        This function computes a matrix of deprivation scores for n zipcodes (rows)
        in d dimensions (columns)
        Inputs:
        cleaned_data    : takes in cleaned processed data
        k               : fixed cutoff in AF method 
        
        Returns deprivation scores as a pandas dataframe
        '''
        merged_data = self.compute_ratios()

        #Generate binary matrix y
        mat_y = pd.DataFrame(index=merged_data.index, columns=self.indicators)
        merged_data['deprivation_share'] = 0
        for ind in self.indicators:
            mat_y[ind] = (merged_data[ind] >= self.thresholds[ind]).astype(int)
            merged_data['deprivation_share'] += mat_y[ind]

        # for all zipcodes that has less than k deprivations assign all 
        # elements to be 0 (following AF methodology)
        mat_y[merged_data['deprivation_share'] <= self.k] = 0
        
        return mat_y


    def normalized_gap(self):
        '''
        Computes the normalized gap - Matrix g^1 in AF method
        Represents the extent of deprivation in distance relative to thresholds
        Some prefer this matrix as it satisfies monotonicity

        Input: Matrix Y from fn:deprivation_matrix()
        Returns: Matrix g^1(k) as a pandas dataframe
        '''
        merged_data = self.compute_ratios()
        mat_y = self.deprivation_matrix()
        
        # Compute the normalized gap - each element is expressed in their respective
        # distance from the deprivation vector (threshold)
        mat_g1 = pd.DataFrame(index=merged_data.index, columns=self.indicators)
        for ind in self.indicators:
            mat_g1[ind] = (merged_data[ind] - self.thresholds[ind]) / self.thresholds[ind]
        
        # Replace null and negative values with 0 
        mat_g1 = mat_g1.fillna(0)
        mat_g1[mat_g1 < 0] = 0
        
        # Apply mat_y to g1
        for ind in self.indicators:
            mat_g1[ind] *= mat_y[ind]

        return mat_g1


    def pca_weights(self, matrix, n_comp, rotate_fn):
        '''
        Performs PCA to express deprivation weights as linear combinations of the
        eigenvectors of the variance-covariance matrix.

        Input: Any Matrix g0, g1, ..., gn (depending on objective of analysis)
        n_comp equivalent to num of dimensions (default=5 (num dimensions), but 
        this parameter is should be set based on scree plot and Kaiser criterion)
        rotate_fn - function for factor rotations (generally: oblimin or varimax)
        Returns: PCA or Factor weights
        '''

        #PCA
        pca = PCA()
        pca.fit(matrix)

        #Generate scree plot
        plt.plot(range(1, len(pca.explained_variance_)+1),
        pca.explained_variance_, 'ro-', linewidth=2)
        plt.title('Scree Plot')
        plt.xlabel('Principal Component')
        plt.ylabel('Eigenvalues')
        plt.show()

        # Factor analysis - Express factors as rotations
        fa = FactorAnalyzer(n_factors=n_comp, rotation= rotate_fn)
        fa.fit(matrix)
        print(pd.DataFrame(fa.get_communalities(), 
                           index=matrix.columns, 
                           columns=['Communalities']))

        # Express weights as factor loadings
        weights = fa.loadings_
        weights = pd.DataFrame(weights, columns=self.indicators)

        # normalize each row to sum to 1 
        # (For principal components, not needed for factor loadings)
        #### weights = weights.abs().div(weights.abs().sum(axis=1), axis=0)
        
        return weights

    def weighted_deprivation_inx(self, matrix, weights):
        '''
        Computes weighted deprivation index for each zipcode

        Inputs: 
            matrix  - g0, g1, ..., gn 
            weights - a dataframe containing vectors of weights for 
                      each dimension
        Returns: Weighted deprivation index score for each zipcode 
        '''
        # Aggregate weights
        weights = weights.sum(axis=0)

        wgt_dpt_idx = matrix.dot(weights)

        # Added standard normalization for visualization:
        wdi_scaled = (wgt_dpt_idx - wgt_dpt_idx.min()) / (wgt_dpt_idx.max() - wgt_dpt_idx.min())

        output_df = pd.DataFrame({'wdi': wgt_dpt_idx,
                                  'wdi_scaled': wdi_scaled}, index=self.data.index)
        return output_df

    def extend_data(self):
        '''
        This function extends the processed dataset with the dimensions needed
        to produce our visualizations.
        '''
        data_extended = (
            self.compute_ratios()
            .join(self.raw_normalized_viz().add_suffix('_norm'))
            .join(self.normalized_gap().add_suffix('_g1').assign(g1_sum=lambda x: x.sum(axis=1)))
            .join(self.weighted_deprivation_inx(self.normalized_gap(), 
                                                self.pca_weights(self.normalized_gap(),
                                                                 n_comp, rotate_fn)))
        )

        # scale g1_sum using min-max scaling
        g1_sum_min = data_extended['g1_sum'].min()
        g1_sum_max = data_extended['g1_sum'].max()
        data_extended['g1_sum_scaled'] = (data_extended['g1_sum'] - g1_sum_min) / (g1_sum_max - g1_sum_min)

        data_extended.to_csv(output_path)
        return None
    

    ## These additional functions were created as part of the AF methodology ##
    ## But were not utilized because their functions are used in specific    ##
    ## policy situations                                                     ##

    def power_gap(self, n):
        '''
        Computes power gap - Matrix g^alpha (n = alpha).
        This matrix is used by policymakers to target the most deprived 
        neighborhoods first

        Input: Matrix g^1(k) from fn: normalized_gap()
        Returns: Matrix g^alpha(k) as a pandas dataframe
        '''
        mat_g2 = self.normalized_gap() ** n
        return mat_g2

    def deprivation_share(self):
        '''
        Computes M0 (Called Adjusted Headcount ratio in the AF method)
        The ratio is a metrics of structural deprivation for those 
        included in cutoff k.

        Input: Matrix Y from fn:deprivation_matrix()
        Returns: A ratio. 
        '''
        mat_y = self.deprivation_matrix()
        non_zero_rows = mat_y.any(axis=1)
        num_non_zero_rows = non_zero_rows.sum()
        denominator = num_non_zero_rows * mat_y.shape[1]
        deprivation_share = mat_y.sum().sum() / denominator

        return deprivation_share

    def adj_deprivation_gap(self):
        '''
        Computes Matrix M1 (called Adjusted Poverty gap in AF method)
        This matrix encodes averages matrix g1 to obtain the average gap 
        (satisfies monotonicity)

        Input: Matrix g1 from fn:normalized_gap()
        Returns: A ratio.
        '''
        mat_g1 = self.normalized_gap()
        non_zero_rows = mat_g1.any(axis=1)
        num_non_zero_rows = non_zero_rows.sum()
        denominator = num_non_zero_rows * mat_g1.shape[1]
        deprivation_share = mat_g1.sum().sum() / denominator

        return deprivation_share
    
    
# Includes call to run from command line.
mdpi = MultiDimensionalDeprivation(k, cleaned_data, thresholds)
mdpi.extend_data()