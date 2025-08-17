"""
AI.FORECAST Implementation

This module provides a Python interface to BigQuery's AI.FORECAST function,
enabling time-series forecasting with a single function call.
"""

import uuid
from typing import List, Dict, Any, Optional, Union
from google.cloud import bigquery
from google.cloud.bigquery import Client
import structlog
from ..config.bigquery_config import get_bigquery_client, get_bigquery_config

logger = structlog.get_logger(__name__)


class Forecaster:
    """BigQuery AI.FORECAST implementation for time-series forecasting."""
    
    def __init__(self, client: Optional[Client] = None):
        """Initialize Forecaster with BigQuery client."""
        self.client = client or get_bigquery_client()
        self.config = get_bigquery_config()
        
    def forecast(
        self,
        time_series_data: List[Dict[str, Any]],
        target_column: str,
        time_column: str,
        forecast_horizon: int = 12,
        model_name: str = "auto",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate time-series forecast using BigQuery AI.FORECAST.
        
        Args:
            time_series_data: List of dictionaries containing time series data
            target_column: Name of the column to forecast
            time_column: Name of the column containing time values
            forecast_horizon: Number of periods to forecast into the future
            model_name: Forecasting model to use ('auto', 'arima', 'prophet', etc.)
            **kwargs: Additional forecasting parameters
            
        Returns:
            Dictionary containing forecast results and metadata
        """
        try:
            # Create unique ID for this forecast
            forecast_id = str(uuid.uuid4())
            
            # Create temporary table with time series data
            temp_table_id = self._create_temp_table(
                time_series_data, target_column, time_column
            )
            
            logger.info("Executing AI.FORECAST query", 
                       forecast_id=forecast_id,
                       model=model_name,
                       data_points=len(time_series_data),
                       forecast_horizon=forecast_horizon)
            
            # Build and execute the AI.FORECAST query
            query = self._build_forecast_query(
                temp_table_id=temp_table_id,
                target_column=target_column,
                time_column=time_column,
                forecast_horizon=forecast_horizon,
                model_name=model_name,
                **kwargs
            )
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from AI.FORECAST")
            
            # Extract forecast results
            forecast_result = results[0].get('ai_forecast_result', {})
            
            # Clean up temporary table
            self._cleanup_temp_table(temp_table_id)
            
            # Store the forecast in BigQuery
            self._store_forecast(
                forecast_id=forecast_id,
                time_series_data=time_series_data,
                target_column=target_column,
                time_column=time_column,
                forecast_horizon=forecast_horizon,
                model_name=model_name,
                forecast_result=forecast_result,
                parameters=kwargs
            )
            
            logger.info("Forecast completed successfully",
                       forecast_id=forecast_id,
                       forecast_periods=len(forecast_result.get('forecast_values', [])))
            
            return {
                'id': forecast_id,
                'forecast_result': forecast_result,
                'model_name': model_name,
                'parameters': {
                    'target_column': target_column,
                    'time_column': time_column,
                    'forecast_horizon': forecast_horizon,
                    **kwargs
                },
                'metadata': {
                    'data_points': len(time_series_data),
                    'forecast_periods': len(forecast_result.get('forecast_values', [])),
                    'timestamp': results[0].get('timestamp', ''),
                    'model_metadata': results[0].get('ai_forecast_metadata', {})
                }
            }
            
        except Exception as e:
            logger.error("Forecast failed",
                        forecast_id=forecast_id if 'forecast_id' in locals() else None,
                        error=str(e),
                        target_column=target_column)
            # Clean up temporary table on error
            if 'temp_table_id' in locals():
                self._cleanup_temp_table(temp_table_id)
            raise
    
    def forecast_from_table(
        self,
        table_id: str,
        target_column: str,
        time_column: str,
        forecast_horizon: int = 12,
        model_name: str = "auto",
        where_clause: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate forecast from existing BigQuery table.
        
        Args:
            table_id: Full BigQuery table ID (project.dataset.table)
            target_column: Name of the column to forecast
            time_column: Name of the column containing time values
            forecast_horizon: Number of periods to forecast into the future
            model_name: Forecasting model to use
            where_clause: Optional WHERE clause to filter data
            **kwargs: Additional forecasting parameters
            
        Returns:
            Dictionary containing forecast results and metadata
        """
        try:
            # Create unique ID for this forecast
            forecast_id = str(uuid.uuid4())
            
            logger.info("Executing AI.FORECAST from table", 
                       forecast_id=forecast_id,
                       table_id=table_id,
                       model=model_name,
                       forecast_horizon=forecast_horizon)
            
            # Build and execute the AI.FORECAST query
            query = self._build_forecast_from_table_query(
                table_id=table_id,
                target_column=target_column,
                time_column=time_column,
                forecast_horizon=forecast_horizon,
                model_name=model_name,
                where_clause=where_clause,
                **kwargs
            )
            
            query_job = self.client.query(query)
            results = list(query_job.result())
            
            if not results:
                raise ValueError("No results returned from AI.FORECAST")
            
            # Extract forecast results
            forecast_result = results[0].get('ai_forecast_result', {})
            
            # Store the forecast in BigQuery
            self._store_forecast(
                forecast_id=forecast_id,
                table_id=table_id,
                target_column=target_column,
                time_column=time_column,
                forecast_horizon=forecast_horizon,
                model_name=model_name,
                forecast_result=forecast_result,
                parameters=kwargs
            )
            
            logger.info("Table-based forecast completed successfully",
                       forecast_id=forecast_id,
                       forecast_periods=len(forecast_result.get('forecast_values', [])))
            
            return {
                'id': forecast_id,
                'forecast_result': forecast_result,
                'model_name': model_name,
                'parameters': {
                    'table_id': table_id,
                    'target_column': target_column,
                    'time_column': time_column,
                    'forecast_horizon': forecast_horizon,
                    'where_clause': where_clause,
                    **kwargs
                },
                'metadata': {
                    'forecast_periods': len(forecast_result.get('forecast_values', [])),
                    'timestamp': results[0].get('timestamp', ''),
                    'model_metadata': results[0].get('ai_forecast_metadata', {})
                }
            }
            
        except Exception as e:
            logger.error("Table-based forecast failed",
                        forecast_id=forecast_id if 'forecast_id' in locals() else None,
                        error=str(e),
                        table_id=table_id)
            raise
    
    def _create_temp_table(
        self,
        time_series_data: List[Dict[str, Any]],
        target_column: str,
        time_column: str
    ) -> str:
        """Create a temporary table with time series data."""
        try:
            # Generate unique table name
            temp_table_name = f"temp_forecast_{uuid.uuid4().hex[:8]}"
            temp_table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.{temp_table_name}"
            
            # Create table schema
            schema = [
                bigquery.SchemaField(time_column, "TIMESTAMP"),
                bigquery.SchemaField(target_column, "FLOAT64")
            ]
            
            # Create the table
            table = bigquery.Table(temp_table_id, schema=schema)
            self.client.create_table(table, exists_ok=True)
            
            # Insert the data
            errors = self.client.insert_rows_json(temp_table_id, time_series_data)
            if errors:
                raise ValueError(f"Failed to insert data into temp table: {errors}")
            
            logger.info("Temporary table created successfully", temp_table_id=temp_table_id)
            return temp_table_id
            
        except Exception as e:
            logger.error("Failed to create temporary table", error=str(e))
            raise
    
    def _cleanup_temp_table(self, temp_table_id: str) -> None:
        """Clean up temporary table after use."""
        try:
            self.client.delete_table(temp_table_id, not_found_ok=True)
            logger.info("Temporary table cleaned up", temp_table_id=temp_table_id)
        except Exception as e:
            logger.warning("Failed to clean up temporary table",
                          temp_table_id=temp_table_id,
                          error=str(e))
    
    def _build_forecast_query(
        self,
        temp_table_id: str,
        target_column: str,
        time_column: str,
        forecast_horizon: int,
        model_name: str,
        **kwargs
    ) -> str:
        """Build the AI.FORECAST SQL query for temporary table."""
        # Build additional parameters
        params = []
        if 'seasonality' in kwargs:
            params.append(f"{kwargs['seasonality']} as seasonality")
        if 'trend' in kwargs:
            params.append(f"'{kwargs['trend']}' as trend")
        if 'confidence_level' in kwargs:
            params.append(f"{kwargs['confidence_level']} as confidence_level")
        
        params_str = ", ".join(params) if params else ""
        params_struct = f"STRUCT({params_str})" if params_str else ""
        
        query = f"""
        SELECT 
            AI.FORECAST(
                TABLE `{temp_table_id}`,
                '{target_column}',
                '{time_column}',
                {forecast_horizon},
                '{model_name}'
                {f", {params_struct}" if params_struct else ""}
            ) as ai_forecast_result,
            CURRENT_TIMESTAMP() as timestamp,
            AI.FORECAST_METADATA() as ai_forecast_metadata
        """
        return query
    
    def _build_forecast_from_table_query(
        self,
        table_id: str,
        target_column: str,
        time_column: str,
        forecast_horizon: int,
        model_name: str,
        where_clause: Optional[str],
        **kwargs
    ) -> str:
        """Build the AI.FORECAST SQL query for existing table."""
        # Build additional parameters
        params = []
        if 'seasonality' in kwargs:
            params.append(f"{kwargs['seasonality']} as seasonality")
        if 'trend' in kwargs:
            params.append(f"'{kwargs['trend']}' as trend")
        if 'confidence_level' in kwargs:
            params.append(f"{kwargs['confidence_level']} as confidence_level")
        
        params_str = ", ".join(params) if params else ""
        params_struct = f"STRUCT({params_str})" if params_str else ""
        
        # Build WHERE clause
        where_sql = f"WHERE {where_clause}" if where_clause else ""
        
        query = f"""
        SELECT 
            AI.FORECAST(
                TABLE `{table_id}` {where_sql},
                '{target_column}',
                '{time_column}',
                {forecast_horizon},
                '{model_name}'
                {f", {params_struct}" if params_struct else ""}
            ) as ai_forecast_result,
            CURRENT_TIMESTAMP() as timestamp,
            AI.FORECAST_METADATA() as ai_forecast_metadata
        """
        return query
    
    def _store_forecast(
        self,
        forecast_id: str,
        target_column: str,
        time_column: str,
        forecast_horizon: int,
        model_name: str,
        forecast_result: Dict[str, Any],
        parameters: Dict[str, Any],
        **kwargs
    ) -> None:
        """Store the forecast result in BigQuery."""
        try:
            table_id = f"{self.config['project_id']}.{self.config['dataset_id']}.forecasts"
            
            # Prepare the row data
            row = {
                'forecast_id': forecast_id,
                'target_column': target_column,
                'time_column': time_column,
                'forecast_horizon': forecast_horizon,
                'model_name': model_name,
                'forecast_result': str(forecast_result),
                'parameters': str(parameters),
                'timestamp': bigquery.ScalarQueryParameter('timestamp', 'TIMESTAMP', None)
            }
            
            # Add additional fields if available
            if 'time_series_data' in kwargs:
                row['data_points'] = len(kwargs['time_series_data'])
            if 'table_id' in kwargs:
                row['source_table'] = kwargs['table_id']
            
            # Insert the row
            errors = self.client.insert_rows_json(table_id, [row])
            if errors:
                logger.warning("Failed to store forecast in BigQuery",
                              forecast_id=forecast_id,
                              errors=errors)
            else:
                logger.info("Forecast stored in BigQuery successfully",
                           forecast_id=forecast_id)
                
        except Exception as e:
            logger.warning("Failed to store forecast in BigQuery",
                          forecast_id=forecast_id,
                          error=str(e))
    
    def get_forecast_metrics(self, forecast_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from forecast results."""
        metrics = {}
        
        if 'forecast_values' in forecast_result:
            forecast_values = forecast_result['forecast_values']
            if forecast_values:
                metrics['mean_forecast'] = sum(forecast_values) / len(forecast_values)
                metrics['forecast_range'] = max(forecast_values) - min(forecast_values)
                metrics['forecast_std'] = self._calculate_std(forecast_values)
        
        if 'confidence_intervals' in forecast_result:
            metrics['has_confidence_intervals'] = True
            metrics['confidence_level'] = forecast_result.get('confidence_level', 0.95)
        
        if 'model_performance' in forecast_result:
            metrics.update(forecast_result['model_performance'])
        
        return metrics
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation of a list of values."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
